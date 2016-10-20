import os
from flask import Flask, render_template, request, g, flash, redirect, url_for, session
from couchdb.design import ViewDefinition
from flaskext.couchdb import CouchDBManager
from flask_bootstrap import Bootstrap
from form import ContactForm
from dataform import *
from userInfo import Login, Register
from imgSearch import imgSearch
from dbDoucment import *
import json

app = Flask(__name__)
bootstrap = Bootstrap(app)
app.secret_key = 'development key'
app.config['UPLOAD_FOLDER'] = 'static/uploads/'
app.config['ALLOWED_EXTENSIONS'] = set(['jpg', 'png', 'tiff', 'jpeg', 'JPG', 'JPEG', 'PNG', 'TIFF'])
app.config.update(
    COUCHDB_SERVER='http://localhost:5984',
    COUCHDB_DATABASE='plantphenotype'
)

views_by_source = ViewDefinition('source', 'findid', '''
    function (doc) {
        if (doc.source && doc.annotation && doc.imglink) {
            emit (doc.source, doc)
        };
    }
    ''')
views_by_user = ViewDefinition('login', 'findPassword', '''
    function (doc) {
        if (doc.username && doc.password) {
            emit(doc.username, doc.password)
        };
    }
    ''')
views_by_Lsysmodel = ViewDefinition('Lsysmodel', 'findUserModel', '''
    function (doc) {
        if (doc.user && doc.src) {
            emit(doc.user, doc)
        };
    }
    ''')
# userInfo & uplaod imgs database
manager = CouchDBManager()
manager.setup(app)
manager.add_viewdef([views_by_source, views_by_user, views_by_Lsysmodel])
manager.sync(app)
# imgs search database
search_obj = imgSearch()

imgId = []
idseq = 0


def image_source(selectedSource):
    sources = []
    for row in views_by_source(g.couch):
        sources.append(row.key)
    sources = list(set(sources))
    sources.sort()
    if selectedSource in sources:
        # move selectedSource to header of list
        sources.remove(selectedSource)
        sources.insert(0, selectedSource)
    return sources


def image_source2():
    sources = ['none']
    for row in views_by_source(g.couch):
        sources.append(row.key)
    sources = list(set(sources))
    return sources


def image_source3(directory):
    global imgId
    for row in views_by_source(g.couch):
        if row.key == directory:
            imgId.append(row.id)


def image_source4(src):
    for row in views_by_source(g.couch):
        if row.value['imglink'] == src:
            return row.id
        else:
            return None


def lsysmodel_user(name):
    for row in views_by_Lsysmodel(g.couch):
        if row.key == name:
            return row.id
    return None


def allowed_files(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']


@app.route('/', methods=['GET', 'POST'])
def index():
    l_login = Login()
    l_register = Register()
    return render_template("index.html", login=l_login, register=l_register)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    form2 = Dataform()
    sources2 = image_source2()
    form2.Sel_Dir.choices = {(x, x) for x in sources2}
    if request.method == 'GET':
        return render_template("upload.html", form=form2)
    elif request.method == 'POST':
        uploaded_files = request.files.getlist("file[]")
        for file in uploaded_files:
            if file and allowed_files(file.filename):
                filename = file.filename
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                try:
                    if form2.Sel_Dir.data == 'none':
                        entry = PlantPhenotype(source=form2.dir_name.data, imglink=filepath,
                                               annotation=form2.Annotation.data)
                        entry.store()
                    else:
                        entry = PlantPhenotype(source=form2.Sel_Dir.data, imglink=filepath,
                                               annotation=form2.Annotation.data)
                        entry.store()
                except Exception as e:
                    flash("Databased error. Failed to Uploaded")
                    return render_template("upload.html", form=form2)
            else:
                flash("File has error. Failed to upload")
                return render_template("upload.html", form=form2)
        flash("Successfully Uploaded")
        return redirect(url_for('dataInsert'))


@app.route('/dataInsertSec', methods=['GET', 'POST'])
def dataInsert():
    global idseq, imgId
    form = ContactForm()
    sources = image_source(form.source.data)
    form.source.choices = [(x, x) for x in sources]
    if request.method == 'POST':
        if request.form['submit'] == 'Simulation':
            entry = PlantPhenotype.load(imgId[idseq])
            matchResult = search_obj.search(entry.imglink)
            print(json.dumps(matchResult, indent=4))
            return render_template("searchResult.html", imgPaths=json.dumps(matchResult))
        if request.form['submit'] == 'Next Picture':
            print("next picture")
            print(len(imgId))
            idseq += 1
            print(idseq)
            if idseq >= len(imgId):
                idseq = len(imgId) - 1
            entry = PlantPhenotype.load(imgId[idseq])
            form.textArea.data = entry.annotation
            return render_template("dataInsertSec.html", name=session.get('name'), form=form,
                                   source=json.dumps(entry.imglink))
        elif request.form['submit'] == 'Prev. Picture':
            print("prev picture")
            idseq -= 1
            if idseq < 0:
                idseq = 0
            entry = PlantPhenotype.load(imgId[idseq])
            form.textArea.data = entry.annotation
            return render_template("dataInsertSec.html", name=session.get('name'), form=form,
                                   source=json.dumps(entry.imglink))
        elif request.form['submit'] == 'Update Source':
            print("update source")
            print(form.source.data)
            imgId = []
            image_source3(form.source.data)
            idseq = 0
            entry = PlantPhenotype.load(imgId[idseq])
            form.textArea.data = entry.annotation
            return render_template("dataInsertSec.html", name=session.get('name'), form=form,
                                   source=json.dumps(entry.imglink))
        elif request.form['submit'] == 'Update Annotation':
            print("update annotation")
            entry = PlantPhenotype.load(imgId[idseq])
            entry.annotation = form.textArea.data
            try:
                entry.store()
                entry = PlantPhenotype.load(imgId[idseq])
                form.textArea.data = entry.annotation
                return render_template("dataInsertSec.html", name=session.get('name'), form=form,
                                       source=json.dumps(entry.imglink))
            except Exception as e:
                flash("Entry error %s", e)
                entry = PlantPhenotype.load(imgId[idseq])
                form.textArea.data = entry.annotation
                return render_template("dataInsertSec.html", name=session.get('name'), form=form,
                                       source=json.dumps(entry.imglink))
    else:
        if sources == []:
            form.textArea.data = ""
            return render_template("dataInsertSec.html", name=session.get('name'), form=form)
        else:
            image_source3(sources[0])
            entry = PlantPhenotype.load(imgId[idseq])
            form.textArea.data = entry.annotation
            return render_template("dataInsertSec.html", name=session.get('name'), form=form,
                                   source=json.dumps(entry.imglink))


@app.route('/updateAnotation', methods=['POST'])
def updateAnotation():
    if request.form is not None:
        print(request.form)
        try:
            plantPhenotype = PlantPhenotype.load(image_source4(request.form['src']))
            plantPhenotype.annotation = request.form['textArea']
            plantPhenotype.height = request.form['height']
            plantPhenotype.width = request.form['width']
            plantPhenotype.area = request.form['area']
            plantPhenotype.size = request.form['size']
            plantPhenotype.weather = request.form['weatherCondition']
            plantPhenotype.soilCondition = request.form['soilCondition']
            plantPhenotype.location = request.form['location']
            plantPhenotype.localSat = request.form['localSat']
            plantPhenotype.store()
            return "Succeed!"
        except Exception as e:
            return "Server Error!"
    else:
        return "Failed!"


@app.route('/login', methods=['POST'])
def login():
    l_form = Login(request.form)
    name = l_form.login_user.data
    password = l_form.login_pass.data
    row = (views_by_user(g.couch))[name]

    # verify username and password
    if l_form.validate():
        try:
            if not row or password != list(row)[0].value:
                flash("Username or password incorrect")
                raise ValueError("Username or password incorrect")
        except Exception as e:
            return redirect(url_for('index'))
    else:
        print("Welcome to the user: ")
        return redirect(url_for('index'))

    # store user name
    session['name'] = l_form.login_user.data
    return redirect(url_for('dataInsert'))


@app.route('/register', methods=['POST'])
def register():
    l_form = Register(request.form)
    if l_form.validate():
        users = Users()
        users.username = l_form.username.data
        users.password = l_form.password.data
        users.email = l_form.email.data
        users.store()
        flash("Congratulation! Register Completed!")
        session['name'] = l_form.username.data
        return redirect(url_for('dataInsert'))
    else:
        flash("Register Error!")
        return redirect(url_for('index'))


@app.route('/LSystem', methods=['POST', 'GET'])
def lsystemModel():
    lsystemform = LSystemform()
    id_model = lsysmodel_user(session.get('name'))

    if id_model is not None:
        entry = LSystemModel.load(id_model)
        lsystemform.speed.data = entry.speed
        lsystemform.scale.data = entry.scale
        lsystemform.depth.data = entry.depth
        lsystemform.maxAngle.data = entry.maxAngle
        lsystemform.minAngle.data = entry.minAngle
        lsystemform.rotation.data = entry.rotation
        lsystemform.velocity.data = entry.velocity
        lsystemform.segment.data = entry.segments
        lsystemform.ruleA.data = entry.rules['ruleA']
        lsystemform.ruleB.data = entry.rules['ruleB']
        lsystemform.ruleC.data = entry.rules['ruleC']
        lsystemform.ruleD.data = entry.rules['ruleD']
        lsystemform.ruleE.data = entry.rules['ruleE']

        lsystemform.imgobj = entry.src #Image.open(BytesIO(base64.b64decode(entry.src)))
        #response = send_file(tempFileObj, as_attachment=True, attachment_filename='myfile.jpg')
        #print(lsystemform.data)
    else:
        lsystemform.speed.data = 1.0
        lsystemform.scale.data = 0.45
        lsystemform.depth.data = 6
        lsystemform.maxAngle.data = 0.60
        lsystemform.minAngle.data = 0.55
        lsystemform.rotation.data = 0.05
        lsystemform.velocity.data = 0.1
        lsystemform.segment.data = 2000
        lsystemform.ruleA.data = "ASLss*[+AL][-AL]///>"
        lsystemform.ruleB.data = ""
        lsystemform.ruleC.data = ""
        lsystemform.ruleD.data = ""
        lsystemform.ruleE.data = ""
        lsystemform.imgobj = "Plant Image"
    return render_template("LSystem.html", name=session.get('name'), image = lsystemform.imgobj, form=lsystemform)


#     imgData = base64.b64decode(imgSrc[22:])
#     leniimg = open('E://img.png', 'wb')
#     leniimg.write(imgData)
#     leniimg.close()

@app.route('/saveModel', methods=['POST'])
def saveModel():
    print(request.form)
    if request.form is not None:
        lSystemModel = LSystemModel()
        lSystemModel.depth = float(request.form['depth'])
        lSystemModel.maxAngle = float(request.form['maxAngle'])
        lSystemModel.minAngle = float(request.form['minAngle'])
        lSystemModel.rotation = float(request.form['rotation'])
        lSystemModel.scale = float(request.form['scale'])
        lSystemModel.segments = float(request.form['segments'])
        lSystemModel.velocity = float(request.form['velocity'])
        lSystemModel.speed = float(request.form['speed'])
        lSystemModel.src = request.form['src'][22:]  # because of the format of base64 image
        lSystemModel.rules = dict(ruleA=request.form['ruleA'], ruleB=request.form['ruleB'],
                                  ruleC=request.form['ruleC'], ruleD=request.form['ruleD'],
                                  ruleE=request.form['ruleE'])
        lSystemModel.user = session.get('name')
        lSystemModel.store()
        return "Succeed!"
    else:
        return "Failed!"


if __name__ == "__main__":
    app.debug = True
    app.run()
