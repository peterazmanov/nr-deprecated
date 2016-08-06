:mod:`nr.utils.cli` --- Commandline interface wrapper
=====================================================

.. module:: nr.utils.cli
  :synopsis: Commandline interface wrapper

The :mod:`~nr.cli` module provides a convenient interface for implementing
wrappers for command-line interfaces. Check out the ``examples/ffmpeg.py``
example.

.. code:: python

  decoder = ffmpeg()
  audio = decoder.decode('my_song.m4a', 44100)
  print("Sound length:", int(audio.length), "seconds")
  print(len(audio), "samples at", audio.hz, "Hz")
  print("Sample at 1.0:", audio.get_sample(1.0))

Cli Class
---------

.. autoclass:: Cli
  :members:
