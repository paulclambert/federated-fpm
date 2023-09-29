import scipy as sp 
import numpy as np 
import tensorflow as tf 

from sklearn.preprocessing import StandardScaler

from splines import NaturalCubicSpline, knots
from optimisation import (gradient_descent_beta, gradient_descent_gamma, 
						  estimate_gamma_gradients, estimate_beta_gradients)


def create_client(X, delta, logtime, n_epochs, learning_rate, n_knots=6, seed=42):

	print("Frac censored:", sum(delta) / delta.size)

	scaler = StandardScaler()
	X = scaler.fit_transform(X)

	knots_x, knots_y = knots(logtime, delta, n_knots)

	ncs = NaturalCubicSpline(knots=knots_x, order=1, intercept=True)

	Z = ncs.transform(knots_y, derivative=False)
	Z_long = ncs.transform(logtime, derivative=False)

	dZ = ncs.transform(logtime, derivative=True)

	return Client(X, Z, dZ, Z_long, delta, logtime, knots_y,
				  n_epochs, learning_rate)


class Client:

	def __init__(self, X, Z, dZ, Z_long, delta, logtime, knots_y, 
				 n_epochs, learning_rate):

		self.X = X 
		self.Z = Z 
		self.dZ = dZ 
		self.Z_long = Z_long
		self.delta = delta
		self.logtime = logtime
		self.knots_y = knots_y

		self.n_epochs = n_epochs
		self.learning_rate = learning_rate

		self.S, self.dS = None, None 
		self.beta, self.gamma = None, None 
		self.loss_beta, self.loss_gamma = [], []

	@property
	def n_samples(self):
		return self.X.shape[0 ]

	def gamma_gradients(self):

		gradients = estimate_gamma_gradients(self.gamma, self.Z, self.knots_y, 
		  		 									     self.learning_rate, self.n_epochs)
		#self.loss_gamma.extend(loss_gamma)
		return gradients

	def beta_gradients(self):

		gradients = estimate_beta_gradients(self.beta, self.X, self.S, self.dS, self.delta,
										  			   self.learning_rate, self.n_epochs)
		#self.loss_gamma.extend(loss_gamma)
		return gradients

	def fit_gamma(self):

		self.gamma, loss_gamma = gradient_descent_gamma(self.gamma, self.Z, self.knots_y, 
		  											    self.learning_rate, self.n_epochs)
		self.loss_gamma.extend(loss_gamma)
		
	def fit_beta(self):
		
		self.beta, loss_beta = gradient_descent_beta(self.beta, self.X, self.S, self.dS, self.delta,
										  			 self.learning_rate, self.n_epochs)
		self.loss_beta.extend(loss_beta)
		
	def update_weights(self, gamma=None, beta=None, update_splines=True):

		if gamma is not None:
			self.gamma = gamma 
	
			if update_splines:
				self.update_splines()

		if beta is not None:
			self.beta = beta 

	def update_splines(self):

		# update spline matrices 
		self.S = self.Z_long @ self.gamma
		self.dS = self.dZ @ self.gamma[1:]
		
		if np.min(self.dS) < 0:
			raise ValueError("Negative values in dS")