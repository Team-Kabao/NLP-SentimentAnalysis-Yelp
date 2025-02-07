import numpy as np
import torch
import torch.nn as nn
from torch.nn import init
import torch.optim as optim
import math
import random
import os
from pathlib import Path 
import time
from tqdm import tqdm
from data_loader import fetch_data
import  matplotlib.pyplot as plt
import os.path

unk = '<UNK>'
# Consult the PyTorch documentation for information on the functions used below:
# https://pytorch.org/docs/stable/torch.html
class FFNN(nn.Module):
	def __init__(self, input_dim, h):
			super(FFNN, self).__init__()
			self.h = h
			self.W1 = nn.Linear(input_dim, h)
			print(input_dim)
			self.activation = nn.ReLU() # The rectified linear unit; one valid choice of activation function
			self.W2 = nn.Linear(h, 5)
			# The below two lines are not a source for an error
			self.softmax = nn.LogSoftmax() # The softmax function that converts vectors into probability distributions; computes log probabilities for computational benefits
			self.loss = nn.NLLLoss() # The cross-entropy/negative log likelihood loss taught in class

	def compute_Loss(self, predicted_vector, gold_label):
		return self.loss(predicted_vector, gold_label)

	def forward(self, input_vector):
		# The z_i are just there to record intermediary computations for your clarity
		z1 = self.activation(self.W1(input_vector))  # BUGG - not activated
		z2 = self.W2(z1)	
		predicted_vector = self.softmax(self.activation(z2))  # BUGG - double activation
		return predicted_vector

# Returns: 
# vocab = A set of strings corresponding to the vocabulary
def make_vocab(data):
	vocab = set()
	for document, _ in data:
		for word in document:
			vocab.add(word)
	return vocab 


# Returns:
# vocab = A set of strings corresponding to the vocabulary including <UNK>
# word2index = A dictionary mapping word/token to its index (a number in 0, ..., V - 1)
# index2word = A dictionary inverting the mapping of word2index
def make_indices(vocab):
	vocab_list = sorted(vocab)
	vocab_list.append(unk)
	word2index = {}
	index2word = {}
	for index, word in enumerate(vocab_list):
		word2index[word] = index 
		index2word[index] = word 
	vocab.add(unk)
	return vocab, word2index, index2word 


# Returns:
# vectorized_data = A list of pairs (vector representation of input, y)
def convert_to_vector_representation(data, word2index):
	vectorized_data = []
	for document, y in data:
		vector = torch.zeros(len(word2index)) 
		for word in document:
			index = word2index.get(word, word2index[unk])
			vector[index] += 1
		vectorized_data.append((vector, y))
	return vectorized_data


def main(hidden_dim, number_of_epochs):
	print("Fetching data")
	train_data, valid_data = fetch_data() # X_data is a list of pairs (document, y); y in {0,1,2,3,4}
	vocab = make_vocab(train_data)
	vocab, word2index, index2word = make_indices(vocab)
	print("Fetched and indexed data")
	train_data = convert_to_vector_representation(train_data, word2index)
	valid_data = convert_to_vector_representation(valid_data, word2index)
	print("Vectorized data")

	model = FFNN(input_dim = len(vocab), h = hidden_dim)
	optimizer = optim.Adagrad(model.parameters(),lr=0.01)
	print("Training for {} epochs".format(number_of_epochs))

	train_accuracy_history = []
	val_accuracy_history = []
	train_loss_history = []
	val_loss_history = []

	for epoch in range(number_of_epochs):
		if os.path.exists("model.pth"):
			state_dict = torch.load("model.pth")['state_dict']
			model.load_state_dict(state_dict)
			print("Successful")

		if len(train_loss_history)>1 and (train_loss_history[-1] < val_loss_history[-1]) and (train_loss_history[-1] < train_loss_history[-2]) and (val_loss_history[-1] > val_loss_history[-2]):
				break

		model.train()
		optimizer.zero_grad()
		loss = None
		totalloss = 0
		correct = 0
		total = 0
		start_time = time.time()
		print("Training started for epoch {}".format(epoch + 1))
		random.shuffle(train_data) # Good practice to shuffle order of training data
		minibatch_size = 16 
		N = len(train_data) 
		for minibatch_index in tqdm(range(N // minibatch_size)):
			optimizer.zero_grad()
			loss = None
			for example_index in range(minibatch_size):
				input_vector, gold_label = train_data[minibatch_index * minibatch_size + example_index]
				predicted_vector = model(input_vector)
				predicted_label = torch.argmax(predicted_vector)
				correct += int(predicted_label == gold_label)
				total += 1
				example_loss = model.compute_Loss(predicted_vector.view(1,-1), torch.tensor([gold_label]))
				if loss is None:
					loss = example_loss
				else:
					loss += example_loss
			loss = loss / minibatch_size	# BUGG - not averaging loss
			totalloss+=loss
			loss.backward()		# BUGGGG - loss and optimzer updated once per epoch
			optimizer.step()
		train_loss_history.append(totalloss/(N // minibatch_size))
		train_accuracy_history.append(correct / total)

		print("Training completed for epoch {}".format(epoch + 1))
		print("Training accuracy for epoch {}: {}".format(epoch + 1, correct / total))
		print("Training time for this epoch: {}".format(time.time() - start_time))
		loss = None
		correct = 0
		total = 0
		start_time = time.time()
		print("Validation started for epoch {}".format(epoch + 1))
		random.shuffle(valid_data) # Good practice to shuffle order of validation data
		minibatch_size = 16 
		N = len(valid_data) 
		#for minibatch_index in tqdm(range(N // minibatch_size)):
			# optimizer.zero_grad()
			# loss = None
			# BUGGGG - Shouldnt train on validation set
			# for example_index in range(minibatch_size):
			# 	input_vector, gold_label = valid_data[minibatch_index * minibatch_size + example_index]
			# 	predicted_vector = model(input_vector)
			# 	predicted_label = torch.argmax(predicted_vector)
			# 	correct += int(predicted_label == gold_label)
			# 	total += 1
			# 	# example_loss = model.compute_Loss(predicted_vector.view(1,-1), torch.tensor([gold_label]))
				# if loss is None:
				# 	loss = example_loss
				# else:
				# 	loss += example_loss
			# loss = loss / minibatch_size
			# loss.backward()
			# optimizer.step()
		val_tot_loss = None
		for i in range(N):
			input_vector, gold_label = valid_data[i]
			predicted_vector = model(input_vector)
			predicted_label = torch.argmax(predicted_vector)
			correct += int(predicted_label == gold_label)
			total += 1
			example_loss = model.compute_Loss(predicted_vector.view(1,-1), torch.tensor([gold_label]))
			if val_tot_loss is None:
				val_tot_loss = example_loss / N
			else:
				val_tot_loss += example_loss / N
		val_accuracy_history.append(correct / total)
		val_loss_history.append(val_tot_loss)
		print("Validation completed for epoch {}".format(epoch + 1))
		print("Validation accuracy for epoch {}: {}".format(epoch + 1, correct / total))
		print("Validation time for this epoch: {}".format(time.time() - start_time))

		#saving model aftr every epoch
		path = "model.pth"
		torch.save({'state_dict': model.state_dict()},path)

	# number of parameters
	print("Number of parameters")
	pytorch_total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
	for p in model.parameters():
		if p.requires_grad:
			print(p.numel())
	print(pytorch_total_params)

	print(train_loss_history)
	print(train_accuracy_history)
	print(val_accuracy_history)
	print(val_loss_history)
    # training loss 
	iteration_list = [i+1 for i in range(number_of_epochs)]
	plt.plot(iteration_list,train_loss_history)
	plt.xlabel("Number of Epochs")
	plt.ylabel("Training Loss")
	plt.title("FFNN: Loss vs Number of Epochs")
    #plt.show()
	plt.savefig('FFFN_train_loss_history.png')
	plt.clf()
    
    # training accuracy 
	iteration_list = [i+1 for i in range(number_of_epochs)]
	plt.plot(iteration_list,train_accuracy_history)
	plt.xlabel("Number of Epochs")
	plt.ylabel("Training Accuracy")
	plt.title("FFNN: Accuracy vs Number of Epochs")
    #plt.show()
	plt.savefig('FFNN_train_accuracy_history.png')
	plt.clf()

    # val accuracy 
	iteration_list = [i+1 for i in range(number_of_epochs)]
	plt.plot(iteration_list,val_accuracy_history,color = "red")
	plt.xlabel("Number of Epochs")
	plt.ylabel("Validation Accuracy")
	plt.title("FFNN: Accuracy vs Number of Epochs")
    #plt.show()
	plt.savefig('FFNN_val_accuracy_history.png')
	plt.clf()

	# val accuracy 
	iteration_list = [i+1 for i in range(number_of_epochs)]
	plt.plot(iteration_list,val_loss_history,color = "red")
	plt.xlabel("Number of Epochs")
	plt.ylabel("Validation Loss")
	plt.title("FFNN: Loss vs Number of Epochs")
    #plt.show()
	plt.savefig('FFNN_val_loss_history.png')
	plt.clf()