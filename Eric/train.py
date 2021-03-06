import matplotlib.pyplot as plt
import seaborn as sns

import numpy as np 
import torch
import time
from collections import OrderedDict

import torch.nn.functional as F
from torch import nn, optim
from torchvision import datasets, models, transforms
from PIL import Image
import json
import argparse

#-------------------------------------------------------------------------------------------------------------------------

parser = argparse.ArgumentParser (description = "Flower Image Classifier")

parser.add_argument('data_dir', help = 'Data directory (default = flowers)', default='../flowers', type = str)
parser.add_argument('--save_dir', help = 'Saving directory', default='./' , type = str)
parser.add_argument('--arch', help = 'Model architecture. Option = vgg19 or densenet121',  default='vgg19',  type = str)
parser.add_argument('--lr', help = 'Learning rate', default=0.001, type = float)
parser.add_argument('--hidden_units', help = 'Number of classifier hidden units in the network ,default = 4096', default=500, type = int)
parser.add_argument('--epochs', help = 'Number of epochs, default = 3', default=1, type = int)
parser.add_argument('--GPU', help = "Option to use 'GPU' (cuda/cpu), default = cuda ", default='cuda', type = str)
parser.add_argument('--dropout', help = "Set dropout rate , default = 0.2", default = 0.2)

arg = parser.parse_args()

#-----------------------------------------------------------------------------------------------------------------------------
# Correction
device = torch.device("cuda" if arg.GPU == 'cuda' and torch.cuda.is_available() else "cpu")

print(device, 'ACTIVATED')

#-----------------------------------------------------------------------------------------------------------------------------

data_dir  = arg.data_dir
train_dir = data_dir + '/train'
valid_dir = data_dir + '/valid'
test_dir  = data_dir + '/test'
#-----------------------------------------------------------------------------------------------------------------------------
data_transform = {'training': transforms.Compose([transforms.RandomResizedCrop(224),
                                           transforms.RandomRotation(30),
                                           transforms.RandomHorizontalFlip(),
                                           transforms.ToTensor(),
                                           transforms.Normalize([0.485, 0.456, 0.406],[0.229, 0.224, 0.225])
                                          ]),
                  
                  'validation': transforms.Compose([transforms.Resize(256),
                                      transforms.CenterCrop(224),
                                      transforms.ToTensor(),
                                      transforms.Normalize([0.485, 0.456, 0.406],[0.229, 0.224, 0.225])
                                         ]),
                  
                  'testing': transforms.Compose([transforms.Resize(256),
                                      transforms.CenterCrop(224),
                                      transforms.ToTensor(),
                                      transforms.Normalize([0.485, 0.456, 0.406],[0.229, 0.224, 0.225])
                                         ])
                 }

image_datasets = { 'train_data': datasets.ImageFolder(train_dir,transform=data_transform['training']),
                  
                  'valid_data' : datasets.ImageFolder(valid_dir,transform=data_transform['validation']),
                  
                  'test_data'  : datasets.ImageFolder(test_dir,transform=data_transform['testing'])
                  }

 
data_loaders = [torch.utils.data.DataLoader(image_datasets['train_data'], batch_size=64, shuffle=True),
                    torch.utils.data.DataLoader(image_datasets['valid_data'], batch_size=64),
                    torch.utils.data.DataLoader(image_datasets['test_data'], batch_size=64)
              ]

#-----------------------------------------------------------------------------------------------------------------------------

with open('cat_to_name.json', 'r') as f:
    flower = json.load(f)

print(json.dumps(flower, sort_keys=True, indent=2, separators=(',', ': ')))

#-----------------------------------------------------------------------------------------------------------------------------

if arg.arch == 'vgg19': # at best the commands are packed into functions so that he argument call can be given when calling the function
    model = models.vgg19(pretrained=True) 
        # Only train the classifier parameters, feature parameters are frozen
    for param in model.parameters():
        param.requires_grad = False
    classifier = nn.Sequential(OrderedDict([
            ('fc1', nn.Linear(25088, 4096)),
            ('relu1', nn.ReLU()),
            ('dropout1', nn.Dropout(p=0.5)),
            ('fc2', nn.Linear(4096, arg.hidden_units)),
            ('relu2', nn.ReLU()),
            ('dropout2', nn.Dropout(p=0.5)),
            ('fc3', nn.Linear(arg.hidden_units, 102)),
            ('output', nn.LogSoftmax(dim=1))
        ]))
    model.classifier = classifier

elif arg.arch == 'Densenet':
    model = models.densenet121(pretrained=True)
    # Only train the classifier parameters, feature parameters are frozen
    for param in model.parameters():
        param.requires_grad = False
    classifier = nn.Sequential(OrderedDict([
        ('fc1', nn.Linear(1024, arg.hidden_units)),
        ('relu', nn.ReLU()),
        ('dropout', nn.Dropout()),
        ('fc2', nn.Linear(arg.hidden_units, 102)),
        ('output', nn.LogSoftmax(dim=1))
    ]))
    model.classifier = classifier

else:
    raise Exception("Architecture not accepted")

""""
    if arg.arch == 'vgg19':
    model = models.vgg19(pretrained=True)

else:
    model = models.densenet121(pretrained=True)

for param in model.parameters():
        param.requires_grad = False


classifier = nn.Sequential(OrderedDict([
('hidden1', nn.Linear(25088, arg.hidden_units)),
('relu', nn.ReLU()),
('dropout', nn.Dropout(arg.dropout)),
('hidden2', nn.Linear(arg.hidden_units, len(flower))),
('output', nn.LogSoftmax(dim=1))
]))

model.classifier = classifier    
"""
model.to(device)

criterion = nn.NLLLoss()
optimizer = optim.Adam(model.classifier.parameters(), lr=arg.lr)        

#-----------------------------------------------------------------------------------------------------------------------------      
    
epochs = arg.epochs
steps = 0
running_loss = 0
print_every = 30
model.to(device)
start = time.time()
for i in range(arg.epochs):
     model.train()
     running_loss = 0
     for inputs, labels in iter(data_loaders[0]):
            steps += 1
        
            inputs, labels = inputs.to(device), labels.to(device) # gpu is not supposed to be hardcoded anywhere
        
            optimizer.zero_grad()
    
            out = model(inputs) # model.forward() is the outdated way of writing this, the new way of doing this is simply writing model() for the forward pass
            loss = criterion(out, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
        
            if steps % print_every == 0:
                test_loss = 0
                accuracy = 0
                model.eval()
            
                with torch.no_grad():
                    for inputs, labels in iter(data_loaders[1]):
                        inputs, labels = inputs.to(device), labels.to(device)
                        out = model.forward(inputs)
                        batch_loss = criterion(out, labels)
                    
                        test_loss += batch_loss.item()
                    
              
                        ps = torch.exp(out)
                        top_p, top_class = ps.topk(1, dim=1)
                        equals = top_class == labels.view(*top_class.shape)
                        accuracy += torch.mean(equals.type(torch.FloatTensor)).item()
                    
                print(f"Epoch {i+1}/{epochs}.. "
                  f"Train loss: {running_loss/print_every:.3f}.. "
                  f"Test loss: {test_loss/len(data_loaders[1]):.3f}.. "
                  f"Test accuracy: {accuracy/len(data_loaders[1]):.3f}")
                running_loss = 0
                model.train()
            
end = time.time()
print(f"The duration of this training is {(end - start)/60} minutes")
    
#-----------------------------------------------------------------------------------------------------------------------------     
  
test_loss = 0
accuracy = 0
model.eval()

with torch.no_grad():
    
    for inputs, labels in iter(data_loaders[2]):
            inputs, labels = inputs.to(device), labels.to(device)
            out = model.forward(inputs)
            batch_loss = criterion(out, labels)
                    
            test_loss += batch_loss.item()
                    
  
            prob = torch.exp(out)
            top_p, top_class = prob.topk(1, dim=1)
            equals = top_class == labels.view(*top_class.shape)
            accuracy += torch.mean(equals.type(torch.FloatTensor)).item()
    
            print(f"test loss: {test_loss/len(data_loaders[2]):.3f}.. "
              f"test accuracy: {accuracy/len(data_loaders[2]):.3f}")    

#-----------------------------------------------------------------------------------------------------------------------------     

checkpoint = arg.save_dir # must be assigned before reference
    
model.class_to_idx = image_datasets['train_data'].class_to_idx
checkpoint = {'model': arg.arch,
              'output': 102,
              'hidden_units': arg.hidden_units,
              'lr': arg.lr,
              'batch_size': 64,
              'epochs': arg.epochs,
              'optimizer': optimizer.state_dict(),
              'state_dict': model.state_dict(),
              'class_to_idx': model.class_to_idx}

torch.save(checkpoint, 'checkpoint.pth')
    

print("Model Saved Succesfully!!!")

