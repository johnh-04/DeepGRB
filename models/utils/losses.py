"""
Custom loss functions for Fermi-GBM neural background estimation.
Compatible across multiple TensorFlow/Keras versions.
"""

import tensorflow as tf

# Gestione compatibilità tra diverse versioni di TensorFlow/Keras
try:
    register_serializable = tf.keras.saving.register_keras_serializable
except AttributeError:
    try:
        register_serializable = tf.keras.utils.register_keras_serializable
    except AttributeError:
        def register_serializable(package="DeepGRB"):
            def decorator(func):
                return func
            return decorator


@register_serializable(package="DeepGRB")
def loss_median(y_true, y_pred):
    """
    Approximation of the Median Absolute Error (L1 pinball / absolute residual).
    """
    diff = tf.abs(y_true - y_pred)
    return tf.reduce_mean(diff, axis=-1)


@register_serializable(package="DeepGRB")
def loss_max(y_true, y_pred):
    """
    Chebyshev / Maximum Error loss to penalize large single-channel residuals.
    """
    diff = tf.abs(y_true - y_pred)
    return tf.reduce_max(diff, axis=-1)