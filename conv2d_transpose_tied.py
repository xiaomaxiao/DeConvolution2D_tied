# -*- coding: utf-8 -*-
from __future__ import absolute_import

from keras import backend as K
from keras.legacy import interfaces

from keras import activations, initializers, regularizers, constraints
from keras.engine import Layer, InputSpec
from keras.utils import conv_utils
from keras.utils.np_utils import to_categorical
from keras.layers import Convolution1D, Conv2D, Conv2DTranspose

import tensorflow as tf

class Conv2DTranspose_tied(Conv2D):
    """Transposed convolution layer (sometimes called Deconvolution).
    The need for transposed convolutions generally arises
    from the desire to use a transformation going in the opposite direction
    of a normal convolution, i.e., from something that has the shape of the
    output of some convolution to something that has the shape of its input
    while maintaining a connectivity pattern that is compatible with
    said convolution.
    When using this layer as the first layer in a model,
    provide the keyword argument `input_shape`
    (tuple of integers, does not include the sample axis),
    e.g. `input_shape=(128, 128, 3)` for 128x128 RGB pictures
    in `data_format="channels_last"`.
    # Arguments
        filters: Integer, the dimensionality of the output space
            (i.e. the number of output filters in the convolution).
        kernel_size: An integer or tuple/list of 2 integers, specifying the
            width and height of the 2D convolution window.
            Can be a single integer to specify the same value for
            all spatial dimensions.
        strides: An integer or tuple/list of 2 integers,
            specifying the strides of the convolution along the width and height.
            Can be a single integer to specify the same value for
            all spatial dimensions.
            Specifying any stride value != 1 is incompatible with specifying
            any `dilation_rate` value != 1.
        padding: one of `"valid"` or `"same"` (case-insensitive).
        data_format: A string,
            one of `channels_last` (default) or `channels_first`.
            The ordering of the dimensions in the inputs.
            `channels_last` corresponds to inputs with shape
            `(batch, height, width, channels)` while `channels_first`
            corresponds to inputs with shape
            `(batch, channels, height, width)`.
            It defaults to the `image_data_format` value found in your
            Keras config file at `~/.keras/keras.json`.
            If you never set it, then it will be "channels_last".
        dilation_rate: an integer or tuple/list of 2 integers, specifying
            the dilation rate to use for dilated convolution.
            Can be a single integer to specify the same value for
            all spatial dimensions.
            Currently, specifying any `dilation_rate` value != 1 is
            incompatible with specifying any stride value != 1.
        activation: Activation function to use
            (see [activations](../activations.md)).
            If you don't specify anything, no activation is applied
            (ie. "linear" activation: `a(x) = x`).
        use_bias: Boolean, whether the layer uses a bias vector.
        kernel_initializer: Initializer for the `kernel` weights matrix
            (see [initializers](../initializers.md)).
        bias_initializer: Initializer for the bias vector
            (see [initializers](../initializers.md)).
        kernel_regularizer: Regularizer function applied to
            the `kernel` weights matrix
            (see [regularizer](../regularizers.md)).
        bias_regularizer: Regularizer function applied to the bias vector
            (see [regularizer](../regularizers.md)).
        activity_regularizer: Regularizer function applied to
            the output of the layer (its "activation").
            (see [regularizer](../regularizers.md)).
        kernel_constraint: Constraint function applied to the kernel matrix
            (see [constraints](../constraints.md)).
        bias_constraint: Constraint function applied to the bias vector
            (see [constraints](../constraints.md)).
    # Input shape
        4D tensor with shape:
        `(batch, channels, rows, cols)` if data_format='channels_first'
        or 4D tensor with shape:
        `(batch, rows, cols, channels)` if data_format='channels_last'.
    # Output shape
        4D tensor with shape:
        `(batch, filters, new_rows, new_cols)` if data_format='channels_first'
        or 4D tensor with shape:
        `(batch, new_rows, new_cols, filters)` if data_format='channels_last'.
        `rows` and `cols` values might have changed due to padding.
    # References
        - [A guide to convolution arithmetic for deep learning](https://arxiv.org/abs/1603.07285v1)
        - [Deconvolutional Networks](http://www.matthewzeiler.com/pubs/cvpr2010/cvpr2010.pdf)
    """

    # @interfaces.legacy_deconv2d_support
    def __init__(self, filters,
                 kernel_size,
                 strides=(1, 1),
                 padding='valid',
                 data_format=None,
                 activation=None,
                 use_bias=True,
                 kernel_initializer='glorot_uniform',
                 bias_initializer='zeros',
                 kernel_regularizer=None,
                 bias_regularizer=None,
                 activity_regularizer=None,
                 kernel_constraint=None,
                 bias_constraint=None,
                 output_shape=None,
                 tied_to=None,
                 **kwargs):
        super(Conv2DTranspose_tied, self).__init__(
            filters,
            kernel_size,
            strides=strides,
            padding=padding,
            data_format=data_format,
            activation=activation,
            use_bias=use_bias,
            kernel_initializer=kernel_initializer,
            bias_initializer=bias_initializer,
            kernel_regularizer=kernel_regularizer,
            bias_regularizer=bias_regularizer,
            activity_regularizer=activity_regularizer,
            kernel_constraint=kernel_constraint,
            bias_constraint=bias_constraint,
            **kwargs)
        self.tied_to = tied_to
        self.transpose_output_shape = output_shape
        self.input_spec = InputSpec(ndim=4)


    def build(self, input_shape):
        if len(input_shape) != 4:
            raise ValueError('Inputs should have rank ' +
                             str(4) +
                             '; Received input shape:', str(input_shape))
        if self.data_format == 'channels_first':
            channel_axis = 1
        else:
            channel_axis = -1
        if input_shape[channel_axis] is None:
            raise ValueError('The channel dimension of the inputs '
                             'should be defined. Found `None`.')
        input_dim = input_shape[channel_axis]
        kernel_shape = self.kernel_size + (self.filters, input_dim)


        kernel = tf.transpose(self.tied_to.kernel, (1, 0, 2, 3))
        self.kernel = kernel


        if self.use_bias:
            self.bias = self.add_weight(shape=(self.filters,),
                                        initializer=self.bias_initializer,
                                        name='bias',
                                        regularizer=self.bias_regularizer,
                                        constraint=self.bias_constraint)
        else:
            self.bias = None
        # Set input spec.
        self.input_spec = InputSpec(ndim=4, axes={channel_axis: input_dim})
        self.built = True

    def call(self, inputs):
        if self.transpose_output_shape is None:
            input_shape = K.shape(inputs)
            input_shape_list = inputs.get_shape().as_list()
            batch_size = input_shape[0]
            if self.data_format == 'channels_first':
                h_axis, w_axis = 2, 3
            else:
                h_axis, w_axis = 1, 2

            height, width = input_shape_list[h_axis], input_shape_list[w_axis]
            kernel_h, kernel_w = self.kernel_size
            stride_h, stride_w = self.strides

            # Infer the dynamic output shape:
            out_height = conv_utils.deconv_length(height,
                                                  stride_h, kernel_h,
                                                  self.padding)

            out_width = conv_utils.deconv_length(width,
                                                 stride_w, kernel_w,
                                                 self.padding)
            if self.data_format == 'channels_first':
                self.transpose_output_shape = (batch_size, self.filters, out_height, out_width)
            else:
                self.transpose_output_shape = (batch_size, out_height, out_width, self.filters)
            shape = self.transpose_output_shape
        else:
            shape = self.transpose_output_shape
            if self.data_format == 'channels_first':
                shape = (shape[0], shape[2], shape[3], shape[1])

            if shape[0] is None:
                shape = (tf.shape(inputs)[0], ) + tuple(shape[1:])
                shape = tf.stack(list(shape))


        outputs = K.conv2d_transpose(x            = inputs,
                                     kernel       = self.kernel,
                                     output_shape = shape,
                                     strides      = self.strides,
                                     padding      = self.padding,
                                     data_format  = self.data_format)
        outputs = tf.reshape(outputs,shape)


        # if self.bias:
        #     outputs = K.bias_add(
        #         outputs,
        #         self.bias,
        #         data_format=self.data_format)

        if self.activation is not None:
            return self.activation(outputs)

        return outputs

    def compute_output_shape(self, input_shape):
        if self.transpose_output_shape is None:
            output_shape = list(input_shape)
            if self.data_format == 'channels_first':
                c_axis, h_axis, w_axis = 1, 2, 3
            else:
                c_axis, h_axis, w_axis = 3, 1, 2

            kernel_h, kernel_w = self.kernel_size
            stride_h, stride_w = self.strides

            output_shape[c_axis] = self.filters
            output_shape[h_axis] = conv_utils.deconv_length(
                output_shape[h_axis], stride_h, kernel_h, self.padding)
            output_shape[w_axis] = conv_utils.deconv_length(
                output_shape[w_axis], stride_w, kernel_w, self.padding)
        else:
            if not isinstance(self.transpose_output_shape, (list, tuple)):
                output_shape = self.transpose_output_shape
            else:
                output_shape = self.transpose_output_shape
        return tuple(output_shape)

    def get_config(self):
        config = {'tied_to': self.tied_to,
                  'output_shape': self.transpose_output_shape}
        base_config = super(Conv2DTranspose, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))