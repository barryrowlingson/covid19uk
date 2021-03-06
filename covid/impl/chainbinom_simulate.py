"""Functions for chain binomial simulation."""

import tensorflow as tf
import tensorflow_probability as tfp
tfd = tfp.distributions


def update_state(update, state, stoichiometry):
    update = tf.expand_dims(update, 1)  # Rx1xN
    update *= tf.expand_dims(stoichiometry, -1)  # RxSx1
    update = tf.reduce_sum(update, axis=0)  # SxN
    return state + update


def chain_binomial_propagate(h, time_step, stoichiometry):
    def propagate_fn(state):
        state_idx, rates = h(state)
        probs = 1 - tf.exp(-rates*time_step)  # RxN
        state_mult = tf.scatter_nd(state_idx[:, None], state,
                                   shape=[state_idx.shape[0], state.shape[1], state.shape[2]])
        update = tfd.Binomial(state_mult, probs=probs).sample()  # RxN
        update = tf.expand_dims(update, 1)  # Rx1xN
        upd_shape = tf.concat([stoichiometry.shape, tf.fill([tf.rank(state)-1], 1)], axis=0)
        update *= tf.reshape(stoichiometry, upd_shape)  # RxSx1
        update = tf.reduce_sum(update, axis=0)
        state = state + update
        return state
    return propagate_fn


def chain_binomial_simulate(hazard_fn, state, start, end, time_step, stoichiometry):

    propagate = chain_binomial_propagate(hazard_fn, time_step, stoichiometry)
    times = tf.range(start, end, time_step)

    output = tf.TensorArray(tf.float64, size=times.shape[0])
    output = output.write(0, state)

    for i in tf.range(1, times.shape[0]):
        state = propagate(state)
        output = output.write(i, state)

    with tf.device("/CPU:0"):
        sim = output.gather(tf.range(times.shape[0]))
    return times, sim
