import numpy as np
import cv2
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
from torch.autograd import Variable
from torch.utils.data import DataLoader
from torchvision import transforms
import torch.backends.cudnn as cudnn
import torchvision
import torch.nn.functional as F
import importlib.util
import hopenet
import utils
from PIL import Image

#https://github.com/haofanwang/accurate-head-pose/blob/master/test_hopenet.py

def load_pose_model(model_PATH):
    """
    load saved model file and export model for training or use
    """
    # ResNet50 structure, 
    model = hopenet.Multinet(torchvision.models.resnet.Bottleneck, [3, 4, 6, 3], 198)

    # Load snapshot of model from file
    saved_state_dict = torch.load(model_PATH, map_location=torch.device('cpu'))
    model.load_state_dict(saved_state_dict)
    return model

def load_img(img, img_PATH=False):
    #set of transformations for incoming images
    #if importing a PIL image from file, set img = None and set img_PATH to path
    #for get image from video, set img to numpy array and leave img_PATH as False
    transformations = transforms.Compose([transforms.Resize(224),
        transforms.CenterCrop(224), transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])])
    if img_PATH:
        img = Image.open(img_PATH)
    else:
        img = Image.fromarray(np.uint8(img)).convert('RGB')
        #img = Image.fromarray(img.astype('uint8'), 'RGB')
    img = transformations(img)
    img = img.unsqueeze(0)

    return img

def define_loss_fn():
    l1loss = torch.nn.L1Loss(size_average=False)
    return l1loss

def run_pose_detection(model, img):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    """
    Get yaw, pitch and roll predictions as float type Tensors of len 1
    """
    model.to(device)
    model.eval()  # Change model to 'eval' mode (BN uses moving mean/var).

    total = 0

    idx_tensor = [idx for idx in range(198)]
    idx_tensor = torch.FloatTensor(idx_tensor).to(device)

    #for i, (images, labels, labels_0, labels_1, labels_2, labels_3, cont_labels, name) in enumerate(test_loader):
    img = Variable(img).to(device)
    
    yaw,yaw_1,yaw_2,yaw_3,yaw_4, pitch,pitch_1,pitch_2,pitch_3,pitch_4, roll,roll_1,roll_2,roll_3,roll_4 = model(img)

    # Binned predictions
    _, yaw_bpred = torch.max(yaw.data, 1)
    _, pitch_bpred = torch.max(pitch.data, 1)
    _, roll_bpred = torch.max(roll.data, 1)

    # Continuous predictions
    yaw_predicted = utils.softmax_temperature(yaw.data, 1)
    pitch_predicted = utils.softmax_temperature(pitch.data, 1)
    roll_predicted = utils.softmax_temperature(roll.data, 1)

    yaw_predicted = torch.sum(yaw_predicted * idx_tensor, 1).cpu() - 99
    pitch_predicted = torch.sum(pitch_predicted * idx_tensor, 1).cpu() - 99
    roll_predicted = torch.sum(roll_predicted * idx_tensor, 1).cpu() - 99
    print(f"Yaw: {yaw_predicted}")
    print(f"Pitch: {pitch_predicted}")
    print(f"Roll: {roll_predicted}")
    return yaw_predicted, pitch_predicted, roll_predicted

def draw_labels(yaw_predicted, pitch_predicted, roll_predicted, img):
    """
    draw box and axis on image, returns the modified image
    """
    # Save first image in batch with pose cube or axis.
    utils.plot_pose_cube(img, yaw_predicted[0], pitch_predicted[0], roll_predicted[0], size=100)
    utils.draw_axis(img, yaw_predicted[0], pitch_predicted[0], roll_predicted[0], tdx = 100, tdy= 100, size=100)
    return img
