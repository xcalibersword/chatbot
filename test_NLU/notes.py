import tensorflow as tf

####max batch size####

# adjust when run out of memory
# large -> 减缓梯度震荡, lower epoch, optimising, faster, each epoch is longer
# too large -> overconfident to stay at the least optimal point
# 10-100 as we prefer mini batch
config = tf.ConfigProto()
config.gpu_options.allow_growth = True
with tf.Session(config=config) as sess:
    pass

####learning rate decay####

#let it decrease as the training proceed
#deep learning every epoch rate halve
#supervised learning set large then slowly decreased
global_step = tf.Variable(0)
#[learning rate not decay|current epoch|decay_steps::decay once every X steps|decay_rate]
learning_rate = tf.train.exponential_decay(0.1, global_step, 1000, 0.98)
optimizer = tf.train.GradientDescentOptimizer(learning_rate).minimize(cost,\
global_step = global_step)
    
