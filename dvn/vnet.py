from net import Network
from keras import regularizers as reg
from keras import optimizers as opt
from keras import backend as K
import numpy as np
import losses as ls
import metrics as mt
import misc as ms

class VNET(Network):
    def __init__(self, nchannels=1, nlabels=2, nlevels=5, nfeats=16, cross_hair=False, activation='tanh', **kwargs):
        inputs = {'main_input': {'shape': (nchannels, None, None, None), 'dtype': 'float32'}}
        cfeats = nfeats
        layers = []

        conv = 'Conv3DCH' if cross_hair else 'Conv3D'
        kernel = (5, 5, 5)
        curinputs = 'main_input'

        for level in  range(nlevels):
            steps = level + 1 if level < 2 else 3
            levelinput = curinputs
            for step in range(steps):
                layers.append(
                    {
                        'layer': conv,
                        'sort':(nlevels-level) * 10 + 9 - step,
                        'inputs': curinputs,
                        'params': {
                            'name': 'encoder_'+str(level)+str(step),
                            'filters': cfeats,
                            'kernel_size': kernel,
                            'strides': (1, 1, 1),
                            'padding': 'same',
                            'activation': activation,
                        }
                    }
                )
                curinputs = 'encoder_'+str(level)+str(step)

            layers.append(
                {
                    'layer': 'Add',
                    'sort': (nlevels-level) * 10 + 9 - (steps + 1),
                    'inputs': [levelinput, curinputs],
                    'params': {
                        'name': 'encoder_' + str(level) + '_final'
                    }
                }
             )
            curinputs = 'encoder_' + str(level) + '_final'

            if level < nlevels - 1:
                layers.append(
                    {
                        'layer': conv,
                        'sort' : (nlevels - level) * 10 + 9 - (steps + 2),
                        'inputs': curinputs,
                        'params': {
                            'name': 'encoder_'+str(level)+'_subsample',
                            'filters': cfeats * 2,
                            'kernel_size': kernel,
                            'strides': (2, 2, 2),
                            'padding': 'same',
                            'activation': activation,
                        }
                     }
                )
                cfeats *= 2

                layers.append(
                    {
                        'layer': 'Concatenate',
                        'inputs': ['encoder_' + str(level) + '_final', 'decoder_'+str(level+1)+'_subsample'],
                        'sort': -((nlevels - level) * 10 + 1),
                        'params': {
                            'axis': 1,
                            'name': 'level_' + str(level) + '_skip_connection'
                        },
                    }
                )
                curinputs = 'level_' + str(level) + '_skip_connection'
                for step in range(steps):
                    layers.append(
                        {
                            'layer': conv,
                            'inputs': curinputs,
                            'sort': -((nlevels - level) * 10 + 2 + step),
                            'params': {
                                'name': 'decoder_'+str(level)+str(step),
                                'filters': cfeats,
                                'kernel_size': kernel,
                                'strides': (1, 1, 1),
                                'padding': 'same',
                                'activation': activation,
                            }
                        }
                    )
                    curinputs = 'decoder_'+str(level)+str(step)

                layers.append({
                    'layer': 'Add',
                    'inputs': ['decoder_'+str(level+1)+'_subsample', curinputs],
                    'sort': -((nlevels-level)*10 + 2 + steps + 1),
                    'params': {
                        'name': 'decoder_' + str(level) + '_final'
                     }
                })

                curinputs = 'decoder_' + str(level) + '_final'

            if level > 0:
                layers.append({
                    'layer': 'Conv3DTranspose',
                    'inputs': curinputs,
                    'sort': -((nlevels - level) * 10 + 2 + steps + 2),
                    'params': {
                        'name': 'decoder_'+str(level)+'_subsample',
                        'filters': cfeats / 2 if level < nlevels-1 else cfeats,
                        'kernel_size': kernel,
                        'strides': (2, 2, 2),
                        'padding': 'same',
                        'activation': activation,
                    }
                })
            else:
                layers.append({
                    'layer': 'Conv3D',
                    'inputs': curinputs,
                    'sort': -((nlevels - level) * 10 + 2 + steps + 3),
                    'params': {
                        'name': 'presoftmax',
                        'filters': nlabels,
                        'kernel_size': (1, 1, 1),
                        'strides': (1, 1, 1),
                        'padding': 'same',
                        'activation': 'linear',
                    }
                })
                layers.append({
                    'layer': 'Softmax',
                    'inputs': 'presoftmax',
                    'sort': -((nlevels - level) * 10 + 2 + steps + 4),
                    'params': {
                        'name': 'output',
                        'axis': 1
                    }
                })

            curinputs = 'encoder_'+str(level)+'_subsample'

        layers = sorted(layers, key=lambda i: i['sort'], reverse=True)

        models = {'default': {'inputs': 'main_input', 'outputs': 'output'}}
        super(VNET, self).__init__(layers=layers, input_shapes=inputs, models=models, **kwargs)

    def compile(self, loss=ls.categorical_crossentropy(1), optimizer='sgd', metrics=['acc'], **kwargs):
        super(VNET, self).compile(models={'default': {'loss': loss, 'optimizer': optimizer, 'metrics': metrics}})

    def fit(self, **kwargs):
        return super(VNET, self).fit(model='default', **kwargs)

    def fit_generator(self, **kwargs):
        return super(VNET, self).fit_generator(model='default', **kwargs)

    def predict_generator(self, **kwargs):
        return super(VNET, self).predict_generator(model='default', **kwargs)

    def predict(self, **kwargs):
        return super(VNET, self).predict(model='default', **kwargs)

    def evaluate(self, **kwargs):
        return super(VNET, self).evaluate(model='default', **kwargs)


if __name__ == '__main__':
    net = VNET(cross_hair=True)
    net.compile()
    N = (10, 1, 64, 64, 64)
    X = np.random.random(N)
    Y = np.random.randint(2, size=N)
    Y = np.squeeze(Y)
    Y = ms.to_one_hot(Y)
    Y = np.transpose(Y, axes=[0,4,1,2,3])
    print 'Testing VNET Network'
    print 'Data Information => ', 'volume size:', X.shape, ' labels:',np.unique(Y)
    net.fit(x=X, y=Y, epochs=10, batch_size=2, shuffle=True)