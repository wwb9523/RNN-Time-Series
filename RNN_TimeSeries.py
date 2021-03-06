# -*- coding: utf-8 -*-
# coding=gbk
"""
Created on Tue May 16 15:23:34 2017
RNN做实数序列预测，来源：http://blog.csdn.net/u010159842/article/details/56014837
@author: tao_tao
"""
import tensorflow.contrib.learn as skflow
import tensorflow as tf
import numpy as np
import pandas as pd


TIMESTEPS=100
RNN_LAYERS=2 
DENSE_LAYERS=None
TRAINING_STEPS=50
BATCH_SIZE=5
PRINT_STEPS=50
LOG_DIR=5

def lstm_model(time_steps, rnn_layers, dense_layers=None):
     def lstm_cells(layers):
         if isinstance(layers[0], dict):
             return [tf.nn.rnn_cell.DropoutWrapper(tf.nn.rnn_cell.BasicLSTMCell(layer['steps']), layer['keep_prob'])
                     if layer.get('keep_prob') else tf.nn.rnn_cell.BasicLSTMCell(layer['steps'])
                     for layer in layers]
         return [tf.nn.rnn_cell.BasicLSTMCell(steps) for steps in layers]
     def dnn_layers(input_layers, layers):
         if layers and isinstance(layers, dict):
             return skflow.ops.dnn(input_layers,
                                   layers['layers'],
                                   activation=layers.get('activation'),
                                   dropout=layers.get('dropout'))
         elif layers:
             return skflow.ops.dnn(input_layers, layers)
         else:
             return input_layers
     def _lstm_model(X, y):
         stacked_lstm = tf.nn.rnn_cell.MultiRNNCell(lstm_cells(rnn_layers))
         x_ = skflow.ops.split_squeeze(1, time_steps, X)
         output, layers = tf.nn.rnn(stacked_lstm, x_, dtype=tf.dtypes.float32)
         output = dnn_layers(output[-1], dense_layers)
         return skflow.models.linear_regression(output, y)
     return _lstm_model
     
def rnn_data(data, time_steps, labels=False):
    """
    creates new data frame based on previous observation
      * example:
        l = [1, 2, 3, 4, 5]
        time_steps = 2
        -> labels == False [[1, 2], [2, 3], [3, 4]]
        -> labels == True [2, 3, 4, 5]
    """
    rnn_df = []
    for i in range(len(data) - time_steps):
        if labels:
            try:
                rnn_df.append(data.iloc[i + time_steps].as_matrix())
            except AttributeError:
                rnn_df.append(data.iloc[i + time_steps])
        else:
            data_ = data.iloc[i: i + time_steps].as_matrix()
            rnn_df.append(data_ if len(data_.shape) > 1 else [[i] for i in data_])
    return np.array(rnn_df)
def split_data(data, val_size=0.1, test_size=0.1):
    """
    splits data to training, validation and testing parts
    """
    ntest = int(round(len(data) * (1 - test_size)))
    nval = int(round(len(data.iloc[:ntest]) * (1 - val_size)))
    df_train, df_val, df_test = data.iloc[:nval], data.iloc[nval:ntest], data.iloc[ntest:]
    return df_train, df_val, df_test
def prepare_data(data, time_steps, labels=False, val_size=0.1, test_size=0.1):
    """
    Given the number of `time_steps` and some data.
    prepares training, validation and test data for an lstm cell.
    """
    df_train, df_val, df_test = split_data(data, val_size, test_size)
    return (rnn_data(df_train, time_steps, labels=labels),
            rnn_data(df_val, time_steps, labels=labels),
            rnn_data(df_test, time_steps, labels=labels))
def generate_data(fct, x, time_steps, seperate=False):
    """generate data with based on a function fct"""
    data = fct(x)
    if not isinstance(data, pd.DataFrame):
        data = pd.DataFrame(data)
    train_x, val_x, test_x = prepare_data(data, time_steps)
    train_y, val_y, test_y = prepare_data(data, time_steps, labels=True)
    return dict(train=train_x, val=val_x, test=test_x), dict(train=train_y, val=val_y, test=test_y)
    
regressor = skflow.TensorFlowEstimator(model_fn=lstm_model(TIMESTEPS, RNN_LAYERS, DENSE_LAYERS),
                                       n_classes=0,
                                       verbose=1,  
                                       steps=TRAINING_STEPS,
                                       optimizer='Adagrad',
                                       learning_rate=0.03,
                                       batch_size=BATCH_SIZE)
                                       
X, y = generate_data(np.sin, np.linspace(0, 100, 10000), TIMESTEPS, seperate=False)
# create a lstm instance and validation monitor
validation_monitor = skflow.monitors.ValidationMonitor(X['val'], y['val'], n_classes=0,
                                                       print_steps=PRINT_STEPS,
                                                       early_stopping_rounds=1000,
                                                       logdir=LOG_DIR)
regressor.fit(X['train'], y['train'], validation_monitor, logdir=LOG_DIR)
# > last training steps
# Step #9700, epoch #119, avg. train loss: 0.00082, avg. val loss: 0.00084
# Step #9800, epoch #120, avg. train loss: 0.00083, avg. val loss: 0.00082
# Step #9900, epoch #122, avg. train loss: 0.00082, avg. val loss: 0.00082
# Step #10000, epoch #123, avg. train loss: 0.00081, avg. val loss: 0.00081

mse = tf.mean_squared_error(regressor.predict(X['test']), y['test'])
print ("Error: {}".format(mse))