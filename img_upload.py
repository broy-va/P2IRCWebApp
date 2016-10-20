import couchdb
import numpy as np
import cv2
import couchdb.client
from couchdb.mapping import Document
from couchdb.mapping import TextField
import os

# "define the folder from where you want to upload your image URI"
IMAGE_FOLDER = "E:\wwwDemo\Webpage\static\PlantPhenotypedata\A1"
couch = couchdb.Server()
cv2.ocl.setUseOpenCL(False)
db = couch.create("img_storage")
server = couchdb.client.Server()
db = server['img_storage']


class ImageStorage(Document):
    img_uri = TextField()
    img_type = TextField()
    img_feature = TextField()
file_list = os.listdir(IMAGE_FOLDER)
orb = cv2.ORB_create()
for imgs in file_list:
    images = IMAGE_FOLDER + "\\" + imgs
    img2 = cv2.imread(images, 0)  # trainImage
    kp2, des2 = orb.detectAndCompute(img2, None)
    imgUrl = "static\PlantPhenotypedata\A1" + "\\" + imgs
    img_upload = ImageStorage(img_uri=imgUrl, img_type='png', img_feature=des2.tolist())
    img_upload.store(db)
    # contact = ImageStorage.load(db, ImageStorage.id)
    # print(contact)
