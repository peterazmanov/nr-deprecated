import sys
import array
from nr.utils import cli

class Audio(object):
  """
  This class represents an Audio data array in memory. The
  Audio object expects to be initialized with an `array.array`
  object.
  """

  def __init__(self, hz, data, stereo):
    if stereo and len(data) % 2 != 0:
      raise ValueError('stereo data must have an even length')

    super(Audio, self).__init__()
    self.hz = int(hz)
    self.data = data
    self.stereo = stereo

  def __len__(self):
    """
    Returns the number of samples in the Audio for
    a single track. If the Audio is stereo, the number of
    samples is actually doubled.
    """

    samples = len(self.data)
    if self.stereo:
      samples /= 2
    return int(samples)

  def __getitem__(self, index):
    """
    Returns a sample at the specified index as a two
    item tuple. If the audio track is mono, the second item
    in the track will be None.
    """

    if self.stereo:
      index *= 2
      return self.data[index], self.data[index + 1]
    else:
      return self.data[index], None

  @property
  def memusage(self):
    return self.data.buffer_info()[1] * self.data.itemsize

  @property
  def length(self):
    """ The length of the audio stream in seconds. """

    seconds = len(self.data) / float(self.hz)
    if self.stereo:
      seconds /= 2
    return seconds

  def get_sample(self, x):
    """ Returns the sample at the specified second *x*. """

    sample_index = int((x / self.length) * len(self))
    return self[sample_index]

class ffmpeg(object):

  def __init__(self, bin_path='ffmpeg'):
    super(ffmpeg, self).__init__()

    self.cli = cli.Cli(bin_path)
    self.cli.request()  #! OSError

  def decode(self, filename, hz, stereo=True):
    with open(filename) as fp:
      pass # raises an error if the file does not exist

    hz = int(hz)
    if hz <= 0:
      raise ValueError('hz must be a positive number')

    response = self.cli.request(
      '-i', filename,
      '-f', 's16le',
      '-acodec', 'pcm_s16le',
      '-ar', str(hz),
      '-ac', ('2' if stereo else '1'),
      '-', # piped (outputs to stdout)
      )
    raw_audio = response.stdout
    if response.returncode != 0:
      err = response.stderr.decode(sys.getdefaultencoding())
      raise ValueError('invalid arguments supplied to ffmpeg\n\n' + err)

    data = array.array('h')
    data.fromstring(raw_audio)
    return Audio(hz, data, stereo)
