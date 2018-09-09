"""This is the jpkfile module. 
It reads content of data archives created with devices by JPK Instruments."""
from struct import unpack
from zipfile import ZipFile
from dateutil import parser
import logging
import numpy as np

formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
log_handler = logging.StreamHandler()
log_handler.setLevel(logging.WARNING)
log_handler.setFormatter(formatter)

#: Dictionary assigning item length (in .dat files) and struckt.unpack abbreviation
#: to the keys used in header files (.properties).
DATA_TYPES = {'short': (2, 'h'),
              'short-data': (2, 'h'),
              'unsignedshort': (2, 'H'),
              'integer-data': (4, 'i'),
              'signedinteger': (4, 'i'),
              'float-data': (4, 'f')}

# NOT COMPLETE, CURRENTLY NOT USED!
# Idea: Chain of conversions for different channels to fall back to
#       if automatic detection of conversion protocols fails, and
#       if no conversion is manually defined in 
#       function JPKSegment.get_decoded_data.
DEFAULT_CONVERSION_CHAIN = {'height': ('nominal',),
                            'vDeflection': ('distance', 'force'),
                            'hDeflection': (),
                            'strainGaugeHeight': (),
                            'error': (),
                            'xSignal1': ()}

#: Dictionary assigning archive type as specified in header files
#: to file extension suffix (e.g. jpk-force, jpk-nt-force).
ARCHIVE_TYPES = {"simple-force-scan-series-header": 'force',
                 "nt-force-scan-series-header": 'nt-force'}

#: Set this to `True` in source file to enable debugging output.
debug = False


def is_segment_header(split):
    return len(split) == 3 and split[2] == "segment-header.properties"


def read_segment_header(self, segment, fname):
    header_f = self._zip.open(fname)
    header_content = header_f.readlines()
    header_content = decode_binary_strings(header_content)
    segment.parameters = parse_header_file(header_content)
    t_end = float(segment
                  .parameters['force-segment-header']['duration'])
    t_step = t_end / float(segment
                           .parameters['force-segment-header']['num-points'])
    segment.data['t'] = (np.arange(0.0, t_end, t_step), {'unit': 's'})
    if self.has_shared_header:
        links = []
        find_links_in_local_parameters(links,
                                       segment.parameters,
                                       self.shared_parameters.keys(), [])
        replace_links(links, segment.parameters,
                      self.shared_parameters)

        
def is_segment_data(split):
    return len(split) == 4 and split[3][-4:] == ".dat"


def read_segment_data(self, segment_number, segment, split, fname):
    channel_label = split[3][:-4]
    data_f = self._zip.open(fname)
    content = data_f.read()
    if debug:
        print(segment_number, channel_label)
    # if no shared header was present, this should work
    if not self.has_shared_header:
        dtype = segment.parameters['channel'][channel_label]['data']['type']
    # otherwise, the chain of keywords is a bit different:
    else:
        dtype = segment.parameters['channel'][channel_label]['type']
    encoder_parameters = None
    if not self.has_shared_header:
        if 'data' in segment.parameters['channel'][channel_label]:
            if 'encoder' in segment.parameters['channel'][channel_label]['data']:
                encoder_parameters = segment.parameters['channel'][channel_label]['data']['encoder']
    else:
        if 'encoder' in segment.parameters['channel'][channel_label]:
            encoder_parameters = segment.parameters['channel'][channel_label]['encoder']

    conversion_parameters = None
    if 'conversion-set' in segment.parameters['channel'][channel_label]:
        if 'conversion' in segment.parameters['channel'][channel_label]['conversion-set']:
            conversion_parameters = segment.parameters['channel'][channel_label]['conversion-set']
    if not encoder_parameters:
        logging.warning("Did not find encoder parameters for channel %s!", split[3][:-4])
    if not conversion_parameters:
        logging.warning("Did not find conversion parameters for channel %s!", split[3][:-4])
    num_points = int(segment.parameters['force-segment-header']['num-points'])

    data = extract_data(content, dtype, num_points)
    segment.data[channel_label] = (data, {'encoder_parameters': encoder_parameters,
                                          'conversion_parameters': conversion_parameters})

    
class JPKFile:
    """Class to unzip a JPK archive and handle access to its headers and data.

    :param fname: Filename of archive to read data from.
    :type fname: str"""
    def __init__(self, fname):        
        """Initializes JPKFile object."""
        self._zip = ZipFile(fname)
        self.data = None
        #: Dictionary containing parameters read from the top level 
        #: ``header.properties`` file.
        self.parameters = {}
        #: Number of segments in archive.
        self.num_segments = 0
        #: Dictionary containing one JPKSegment instance per segment.
        self.segments = {}
        self.archive_type = ""
        #: Will be set to ``True`` if archive has a shared header, ``False`` otherwise
        self.has_shared_header = False
        #: ``None`` if no shared header is present, dictionary containing parameters otherwise.
        self.shared_parameters = None

        # create list of file names in archive (strings, not only file handles).
        list_of_filenames = [f.filename for f in self._zip.filelist]

        self.read_files(list_of_filenames)

    def read_files(self, list_of_filenames):
        """Crawls through list of files in archive and processes them automatically
        by name and extension. It populates :py:attr:`parameters` and :py:attr:`segments` 
        with content. For different file types present in JPK archives, 
        have a look at the :doc:`structure of JPK archives <structure>`."""
        # top header should also be present and the first file in the filelist.
        top_header = list_of_filenames.pop(list_of_filenames.index('header.properties'))
        top_header_f = self._zip.open(top_header)
        top_header_content = top_header_f.readlines()
        top_header_content = decode_binary_strings(top_header_content)
        
        # parse content of top header file to self.parameters.
        self.parameters.update(parse_header_file(top_header_content))
        # if shared header is present ...
        if list_of_filenames.count("shared-data/header.properties"):
            # ... set this to True,
            self.has_shared_header = True
            self.shared_parameters = {}
            # and remove it from list of files.
            shared_header = list_of_filenames.pop(
                list_of_filenames.index("shared-data/header.properties"))
            shared_header_f = self._zip.open(shared_header)
            shared_header_content = shared_header_f.readlines()
            shared_header_content = decode_binary_strings(shared_header_content)
            # Parse header content to dictionary.
            self.shared_parameters.update(parse_header_file(shared_header_content))
        # The remaining files should be structured in segments.
        # The loop is checking for every file in which segment folder it is, and 
        # whether it's a segment header or data file.
        # For each new segment folder it encounters, a JPKSegment object is created
        # and added to the self.segments dictionary.
        # The JPKSegment is then populated by contents of the segment's
        # header and data files.
        segment = None
        for fname in list_of_filenames:
            split = fname.split("/")
            if split[0] == "segments":
                if len(split) < 3:
                    continue                
                segment_number = int(split[1])  # `split[1]` should be the segment's number.                
                if segment_number > self.num_segments - 1:
                    new_JPKSegment = JPKSegment(self.has_shared_header, self.shared_parameters)
                    new_JPKSegment.index = segment_number
                    segment = new_JPKSegment
                    self.segments[segment_number] = segment
                    self.num_segments += 1                        
                if is_segment_header(split):
                    read_segment_header(self, segment, fname)
                # .dat is the extension for data files.
                elif is_segment_data(split):
                    read_segment_data(self, segment_number, segment, split, fname)                                                                
            else:
                logger = logging.getLogger("JPKFile.read_files")
                logger.addHandler(log_handler)
                msg = "Encountered new folder '%s'.\n" % split[0]
                msg += "Do not know how to handle that."
                logger.warning(msg)
            
    def get_array(self, channels=[], decode=True):
        """
        Returns channel data from all segments in a numpy array; in addition, reads physical 
        units as specified by header files.

        :param channels: List of channels (channel names, i.e. strings) of which to return data.
        :param decode: Determines whether data is to be decoded, i.e. transformed according to 
        transformation parameters defined in header files.
        :type decode: bool
        :return: Tuple with two items: (1) Numpy array with labeled columns, one column 
        per requested channel; (2) dictionary assigning units to channels."""
        present_in_all_segments = check_requested_channels_in_all_segments(channels, self)            
        
        if present_in_all_segments:
            # reads data and units of first segment
            data, units = self.segments[0].get_array(channels, decode)
            for i in range(1, len(self.segments)):
                s = self.segments[i]
                d, u = s.get_array(channels, decode)
                if u == units:
                    # concatenates data of segment `i` to array `data`
                    data = np.concatenate((data, d))
                else:
                    msg = "ERROR in JPKFile.get_array!\nCould not concatenate"
                    msg += "data of all segments: units not matching\n"
                    raise RuntimeError(msg)
            return data, units
        else:
            msg = "I recommend extracting data of segments separately by using"
            msg += " JPKFile.segments[i].get_array(channels = [...])."
            logging.warning(msg)
            return None, None

    def get_info(self, issue='general'):
        """
        Request a string on a certain issue.  
        Currently only one `issue` keyword is possible: 'segments'. This returns a 
        summary/overview on segment properties.

        :param issue: Keyword/issue on which to request information.
        :type issue: str
        :return: String on requested issue.
        """
        if issue == 'segments':
            s = ""
            s = s + "=" * 70 + "\n"
            s = s + "SEGMENT\tTYPE\tNUM POINTS\tDURATION\n"
            s = s + "-------\t----\t----------\t--------\n"            
            for i in range(len(self.segments)):
                s = s + str(i) + "\t" + self.segments[i].get_info('type') + "\t" + \
                    self.segments[i].get_info('num-points') \
                    + '\t\t' + self.segments[i].get_info('duration') + '\n'
            s = s + "=" * 70 + "\n"            
        return s

    
def check_requested_channels_in_all_segments(channels, self):
    present_in_all_segments = True
    for i in range(self.num_segments):
        for c in channels:
            if c not in self.segments[i].data:
                present_in_all_segments = False
                logging.warning("requested channel %s not present in segment %i.", c, i)
                break
    return present_in_all_segments


class JPKSegment:
    """
    Class to hold data and parameters of a single segment in a JPK archive.
    It is usually created internally when handling a JPK archive with the JPKFile class.
    
    :param parent_has_shared_header: True, if JPKFile finds shared header in JPK archive, 
     False otherwise.
    :type parent_has_shared_header: bool
    :param shared_properties: If parent_has_shared_header is True, this parameter needs to 
    hold the dictionary containing the header's contents. Otherwise it is None."""
    def __init__(self, parent_has_shared_header=False, shared_properties=None):
        """Constructor."""
        #: Dictionary holding parameters read from segment header.
        self.parameters = {}
        #: Dictionary assigning numpy arrays containing data and definitions on how 
        #: to convert raw data to physical data to all channels present in this segment.
        self.data = {}
        self.index = None
        self.parent_has_shared_header = parent_has_shared_header
        self.shared_properties = shared_properties

    def get_time(self, offset=0):
        """Returns time-stamps, increased by possible offset."""
        return self.data['t'][0] + offset

    def get_array(self, channels=[], decode=True):
        """
        Constructs a numpy array containing data of given channels. If `decode` is True (default),
        data is converted following conversions defined in segment's header (or shared header).

        :param channels: List of channels (channel names, i.e. strings) of which to return data.
        :param decode: Determines whether data is to be decoded, i.e. transformed according 
         to transformation parameters defined in header files.
        :type decode: bool
        :return: Tuple with two items: (1) Numpy array with labeled columns, one column per 
         requested channel; (2) dictionary assigning units to channels.
        """
        _data = {}
        dtypes = []
        shape = self.data[channels[0]][0].shape
        units = {}

        for c in channels:
            if c == 't':
                d = self.data['t'][0]
                unit = 's'
            elif decode:
                d, unit = self.get_decoded_data(c)            
            else:
                d, unit = (self.data[c][0], 'digital', 0)
            print(d.shape)
            print(shape)
            if d.shape[0] != shape[0]:
                msg = "ERROR! Number of points in data channel '%s'" % c
                msg += "does not match expected number of %i\n" % shape[0]
                raise RuntimeError(msg)
            _data[c] = d
            dtypes.append((c, d.dtype))
            units[c] = unit
        A = np.zeros(shape, dtype=dtypes)
        for c in channels:
            A[c] = _data[c]
        return A, units        

    def get_decoded_data(self, channel, conversions_to_be_applied='auto'):
        """
        Get decoded data of one channel. 'decoded' here means the raw, digital data 
        gets converted (to physical data) following certain conversion steps. These steps
        should be defined in the JPK archive's header files. This routine tries to 
        read those conversion steps from those header files by default 
        (`conversions_to_be_applied='auto'`). Alternatively, you can pass a list of
        conversion keywords as `conversions_to_be_applied` manually
        (see documentation on :doc:`JPK archive structures <structure>` for an overview
        of what I think how conversion rules are stored in the header files ...).
        
        :param channel: Name of channel to convert data of.
        :type channel: str
        :param conversions_to_be_applied: Specifying what conversions to apply, 
         see description above.
        :return: Tuple with 2 items; 
         (1) Single-column numpy array containing converted data; 
         (2) Unit as read for last conversion step from header file.
        """
        unit = 'digital'

        encoder_parameters = self.data[channel][1]['encoder_parameters']
        conversion_parameters = self.data[channel][1]['conversion_parameters']['conversion']
        data = self.data[channel][0]

        raw = data[:]
        # Independet of `conversions_to_be_applied`, the first step of conversion
        # apparently has to be as defined by encoder parameters.
        if encoder_parameters:
            if encoder_parameters['scaling']['style'] == 'offsetmultiplier':
                multiplier_raw = float(encoder_parameters['scaling']['multiplier'])
                offset_raw = float(encoder_parameters['scaling']['offset'])
                raw = multiplier_raw * raw + offset_raw

                unit = encoder_parameters['scaling']['unit']['unit']
            else:
                msg = "ERROR! Can only handle converters of type 'offsetmultiplier' so far."
                raise RuntimeError(msg)

        else:
            logging.warning("No encoder parameters found for channel '%s'.\n", channel)

        # If conversions_to_be_applied is a string, it should be either 'default' or 'auto'.
        # I recommend always using auto, unless you encounter any problems due to conversion.
        if type(conversions_to_be_applied) == str:
            if conversions_to_be_applied == 'default':                
                conversions_to_be_applied = DEFAULT_CONVERSION_CHAIN[channel]
                if len(conversions_to_be_applied) == 0:
                    msg = """You request decoding of a channel for which no
default conversion scheme is present. You can apply 
a temporary conversion scheme by passing a list or tuple
of conversion key words in the parameter 
conversions_to_be_applied. When I
created this module, I did not have enough examples to
set default schemes for all channels. You can extend the
module to include your own default chain of conversion to
be applied at the top of the file jpkfile.py.
Change the tuples in DEFAULT_CONVERSION_CHAIN of 
conversion keys to match your desired conversion scheme.
Also, it would be awesome if you could let me know what
default conversion scheme works for you, so I could 
probably include it in the latest version of jpkfile.
Just send me a mail to ilyasp.ku@gmail.com. THANKS!"""
                    logging.warning(msg)
            elif conversions_to_be_applied == 'auto':
                conversions_to_be_applied = determine_conversions_automatically(
                    self.data[channel][1]['conversion_parameters'])
            else:
                msg = "Unknown string '%s' for" % conversions_to_be_applied
                msg += " function JPKFile.get_decoded_data's parameter conversions_to_be_applied.\n"
                msg += "Valid strings: 'auto' and 'default'.\nWill now use 'auto'."
                logging.warning(msg)
                conversions_to_be_applied = determine_conversions_automatically(
                    self.data[channel][1]['conversion_parameters'])

        if conversion_parameters:

            conversion_keys = conversion_parameters.keys()
            for c in conversions_to_be_applied:

                if c not in conversion_keys:
                    msg = "Requested conversion '%s' can't be applied,\nno parameters for '%s' found in jpk header." % (c,c)
                    raise RuntimeError(msg)
                else:
                    if conversion_parameters[c]['defined'] == 'false':
                        msg = "Requested conversion '%s' can't be applied!\n" % c
                        msg += "This conversion was specified as not defined\nin jpk header file." 
                        raise RuntimeError(msg)

            if debug:
                print("=" * 70)
                print("APPLYING CONVERSIONS")
            for c in conversions_to_be_applied:
                if debug:
                    print(c)
                if conversion_parameters[c]['scaling']['style'] == 'offsetmultiplier':

                    multiplier = float(conversion_parameters[c]['scaling']['multiplier'])
                    offset = float(conversion_parameters[c]['scaling']['offset'])

                    raw = raw * multiplier + offset

                    unit = conversion_parameters[c]['scaling']['unit']['unit']

                else:
                    msg = "ERROR! Can only handle converters of type 'offsetmultiplier' so far."
                    raise RuntimeError(msg)
        else:
            logging.warning("No conversion parameters found for channel '%s'.", channel)
                        
        return raw, unit

    def get_info(self, issue='general'):
        """
        Request information (string) on some issue.
        This is basically just a more user-friendly assignment of
        parameters of interest to single keywords.
        For the `issue` parameter the following strings are valid:
         * 'general' (default)
         * 'channels'
         * 'num-points'
         * 'duration'
         * 'type'

        :param issue: Keyword specifying what kind of information is asked for.
        :type issue: str
        :return: String or list of strings containing requested information.
        """

        if not self.parent_has_shared_header:
            d = {'channels': self.parameters['channels']['list'],
                 'num-points': self.parameters['force-segment-header']['num-points'],
                 'duration': self.parameters['force-segment-header']['duration'],
                 'type': self.parameters['force-segment-header']['settings']['style']}
        else:
            if 'force-segment-header-info' in self.parameters['force-segment-header']:
                d = {'channels': self.parameters['channels']['list'],
                     'num-points': self.parameters['force-segment-header']['num-points'],
                     'duration': self.parameters['force-segment-header']['duration']}
                d['type'] = self.shared_properties['force-segment-header-info'][self.parameters['force-segment-header']['force-segment-header-info']['*']]['settings']['style']
            else:
                d = {'channels': self.parameters['channels']['list'],
                     'num-points': self.parameters['force-segment-header']['num-points'],
                     'duration': self.parameters['force-segment-header']['duration'],
                     'type': self.parameters['force-segment-header']['settings']['style']}
    
        if not issue == 'general':
            return d[issue]
        else:
            s = "=" * 70 + "\n"
            s = s + " " * 10 + "GENERAL INFORMATION ON SEGMENT WITH INDEX "
            s = s + str(self.index) + "\n"
            s = s + "=" * 70 + "\n"
            s = s + "Type of segment:\n" + " " * 4 + self.get_info('type') + "\n"
            s = s + "List of channels:\n" + " " * 4 + self.get_info('channels') + "\n"
            s = s + "Each of those channels should contain " + self.get_info('num-points')
            s = s + " data points,\n" + " " * 4 + "recorded in " + self.get_info('duration')
            s = s + " seconds (OR WHAT IS UNIT OF TIME?)" + "\n"
            s = s + "=" * 70 + "\n"
            return s
            

class JPKMap:
    """
    Loads a JPK map file (ending on '.jpk-force-map') to the buffer. This map consists
    of multiple 'pixels', each of which is a single force recording at one position.
    This makes maps a collection of recordings. To get the single pixels to work in 
    a similar way as the JPKFile objects and to make the whole module more modular (!?) ,
    I created a class based on `JPKFile` called :py:class:`~jpkfile._JPKFileForJPKMap`, which 
    requires a :py:class:`~jpkfile._VirtualZipFile` object instead of the path to a zip file. 
    This makes the whole concept a bit harder to follow, but it makes the pixels 
    behave as JPKFile objects. This class is not yet outfitted with many helpful 
    functions to retrieve or analyse data of the map. The problem is, I don't really
    know what is useful and what isn't, since I never worked with maps. If you want a 
    feature added, feel free to send me a message or open an issue on github or implement 
    it yourself and send a pull request.

    :param fname: Path to force map (zip archive, usually ending on '.jpk-force-map').
    :type fname: str
    """
    def __init__(self, fname):
        """Constructor"""
        self._zip = ZipFile(fname)
            
        self.num_indices = 0
        #: Dictionary containing JPKFile instances, one per pixel, indexed with flat indices.
        self.flat_indices = {}
        #: Dictionary holding parameters stored in top level header file.
        self.parameters = {}

        self.has_shared_header = False
        self.shared_parameters = None
        
        self.read_files()

    def read_files(self):
        """Crawls through list of files in archive and processes them automatically
        by name and extension. It populates :py:attr:`parameters` and :py:attr:`flat_indices` 
        with content. For different file types present in JPK archives, 
        have a look at the :doc:`structure of JPK archives <structure>`."""
        list_of_filenames = [f.filename for f in self._zip.filelist]

        top_header_f = self._zip.open(list_of_filenames.pop(
            list_of_filenames.index('header.properties')))
        top_header_content = top_header_f.readlines()
        top_header_content = decode_binary_strings(top_header_content)

        # parse content of top header file to self.parameters.
        self.parameters.update(parse_header_file(top_header_content))

        if list_of_filenames.count("shared-data/header.properties"):
            # ... set this to True,
            self.has_shared_header = True
            self.shared_parameters = {}
            # and remove it from list of files.
            shared_header = list_of_filenames.pop(
                list_of_filenames.index("shared-data/header.properties"))
            shared_header_f = self._zip.open(shared_header)
            shared_header_content = shared_header_f.readlines()
            shared_header_content = decode_binary_strings(shared_header_content)
            # Parse header content to dictionary.
            self.shared_parameters.update(parse_header_file(shared_header_content))

        index_lists_of_filenames = {}

        for fname in list_of_filenames:
            
            split = fname.split("/")

            if split[0] == "index":
                if len(split) < 3:
                    pass
                else:
                    index = int(split[1])

                    if index > self.num_indices - 1:
                        
                        index_lists_of_filenames[index] = []
                        self.num_indices += 1
                        
                    _fname = '/'.join(split[2:])
                    if _fname:
                        index_lists_of_filenames[index].append(_fname)

        for i in index_lists_of_filenames.keys():
            virtual_zip = _VirtualZipFile(
                self._zip, index_lists_of_filenames[i], "index/" + str(i) + "/")
            new_JPKFile = _JPKFileForJPKMap(
                virtual_zip, self.has_shared_header, self.shared_parameters)
            self.flat_indices[i] = new_JPKFile
                    
    def get_single_pixel(self, index):
        """
        Returns JPKFile instance of a single pixel.

        :param index: Integer for flat indices or tuple/list of two 
         integers for grid coordinates pointing to desired pixel.
        """
        pattern_type = self.parameters['force-scan-map']['position-pattern']['type']
        
        if pattern_type == 'grid-position-pattern':
            if type(index) == tuple or type(index) == list:
                i = int(self.parameters['force-scan-map']['position-pattern']['grid']['ilength'])
                j = int(self.parameters['force-scan-map']['position-pattern']['grid']['jlength'])
                if i > index[0] and j > index[1]:
                    return self.flat_indices[i * index[0] + index[1]]
                else:
                    msg = "Index is [%i,%i], but max range is limited to [%i,%i].\n" % (index[0],index[1],i-1,j-1)
                    raise RuntimeError(msg)

            else:
                msg = "Detected grid pattern for this map, you should\n"
                msg += "specify index as a list/tuple of two values, i-index and j-index."
                logging.warning(msg)
                if type(index) == int:
                    msg = "Your index is an integer. "
                    msg += "Trying to return an item using the flattened grid coordinates."
                    logging.warning(msg)
                    return self.flat_indices[index]
                else:
                    logging.warning("Returning None")
                    return
            

class _VirtualZipFile:
    """
    THIS CLASS SHOULD NEVER BE USED DIRECTLY. IT IS USED INDIRECTLY VIA `JPKMap`.
    *Virtual* ZipFile class, to make the functionality of the real ZipFile class 
    available for a subfolder of real zip archives. I implemented this to be able
    to use the familiar JPKFile class for each pixel of a force map. This way,
    only few things have to be adjusted in JPKFileForJPKMap, which inherits
    JPKFile, to make every pixel available as a JPKFile instance.

    :param parent_zip: ZipFile instance holding the subfolder that is to 
     be governed by this _VirtualZipFile.
    :type parent_zip: ZipFile
    :param excerpt_list_of_filenames: List of filenames (strings) containing 
     only files of the subfolder; path has to be relative as if looking from within the subfolder.
    :param prefix: Path prefix, i.e., path to the subfoler. This is used 
     to construct the complete path to each file for the real ZipFile instance.
    :type prefix: str
    """
    def __init__(self, parent_zip, excerpt_list_of_filenames, prefix):
        
        #: (Pointer to) Real ZipFile instance, containing this _VirtualZipFile's folder.
        self.parent_zip = parent_zip

        #: List of filenames (strings) containing only files of the subfolder; 
        #: Paths have to be relative as if looking from within the subfolder.
        #: For example, if your complete zip archive (see files in `parent_zip`)
        #: has a folder called 'A', and it contains a file named 'bla.txt',
        #: its path will be 'A/bla.txt' in the real ZipFile. In a
        #: `_VirtualZipFile` supposed to govern the contents of folder 'A',
        #: the path has to be only 'bla.txt', however.
        self.list_of_filenames = excerpt_list_of_filenames

        #: Prefix to the folder governed by this _VirtualZipFile.
        #: Referring to the example above, this needs to be 'A/'.
        #: It will be used to pass the complete path to the `parent_zip`.
        self.prefix = prefix

    def open(self, fname):
        return self.parent_zip.open(self.prefix + fname)

    
class _JPKFileForJPKMap(JPKFile):
    """
    THIS CLASS SHOULD NEVER BE USED DIRECTLY. IT IS USED INDIRECTLY VIA `JPKMap`.
    This class is derived from JPKFile; its purpose is to make the JPKFile class,
    which is designed to provide a user interface to data of a single measurement
    or recording, available for use with JPKMap (force maps) which is a 
    collection of multiple recordings.

    :param virtual_zip: (Pointer to) _VirtualZipFile for the subdirectory.
    :param has_shared_header: `True` if parent `JPKMap` has a shared header, `False` otherwise.
    :param shared_parameters: `None` if no shared header present, 
     a dictionary containing parameters read from shared header otherwise."""
    def __init__(self, virtual_zip, has_shared_header, shared_parameters):

        self._zip = virtual_zip
        self.data = None
        #: Dictionary containing parameters read from the top level 
        #: ``header.properties`` file.
        self.parameters = {}
        #: Number of segments in archive.
        self.num_segments = 0
        #: Dictionary containing one JPKSegment instance per segment.
        self.segments = {}
        self.archive_type = ""
        #: Will be set to ``True`` if archive has a shared header, ``False`` otherwise
        self.has_shared_header = has_shared_header
        #: ``None`` if no shared header is present, dictionary containing parameters otherwise.
        self.shared_parameters = shared_parameters

        list_of_filenames = self._zip.list_of_filenames

        self.read_files(list_of_filenames)
        
        self.index = None

        
def determine_conversions_automatically(conversion_set_dictionary):
    """
    Takes all parameters on how to convert some channel's data read from a header file 
    to determine the chain of conversion steps automatically.
    
    :param conversion_set_dictionary: Dictionary of 'conversion-set' 
     parameters as parsed from header file with function `parse_header_file`.
    :type conversion_set_dictionary: dict
    :return: List of conversion keywords."""

    # Conversions is a list that will hold the converion keywords.
    # When populating this list in the following while loop, the 
    # order of conversions needs to be reversed. The list is 
    # initiated in the following line with the last conversion step's
    # keyword as first item.
    conversions = [conversion_set_dictionary['conversions']['default']]
    # This is the name of the first conversion to be applied (usually
    # from digital back to the analogue potential in voltage).
    raw_name = conversion_set_dictionary['conversions']['base']

    # This lits should contain keywords of all conversions necessary to 
    # go from first conversion (`raw_name`) to last (first item in `conversions`)    
    chain_complete = False
    if conversions[0] == raw_name:
        chain_complete = True
        conversions = []
    while not chain_complete:
        key = conversions[-1]
        previous_conversion = conversion_set_dictionary['conversion'][key]['base-calibration-slot']
        if previous_conversion == raw_name:
            # Completion is reached when the name of the preceding converion 
            # matches that of the first converion.
            chain_complete = True
        else:
            conversions.append(previous_conversion)
    
    conversions.reverse()
    return conversions


def extract_data(content, dtype, num_points):
    """
    Converts data from contents of .dat files in the JPKArchive to
    python-understandable formats.
    This function requires the binary `content`, the `dtype` of the 
    binary content as read from the appropiate header file, and the
    number of points as specified in the header file to double check
    the conversion.

    :param content: Binary content of a .dat file.
    :type content: str
    :param dtype: Data type as read from heade file.
    :type dtype: str
    :param num_points: Expected number of points encoded in binary content.
    :type num_points: int
    :return: Numpy array containing digital (non-physical, unconverted) data."""
    point_length, type_code = DATA_TYPES[dtype]

    data = []
    
    for i in range(int(len(content) / point_length)):
        data.append(unpack('!' + type_code, content[i * point_length:(i + 1) * point_length]))

    if len(data) == num_points:
        return np.array(data)
    else:
        msg = "ERROR! Number of extracted data points is %i," % len(data)
        msg += " and does not match the number of present data points %i" % num_points
        msg += " as read from the segment's header file."
        raise RuntimeError(msg)


def parse_header_file(content):
    header_dict = {}
    start = 0

    if str(content[start][:2]) == "##":
        start = 1

    try:
        from pytz import utc
        fmt = '%Y-%m-%d %H:%M:%S %Z%z'
        t = utc.localize(parser.parse(str(content[start][1:]), dayfirst=True)).strftime(fmt)
    except:
        t = parser.parse(content[start][1:])

    header_dict['date'] = t

    for line in content[start + 1:]:
        key, value = str(line).split('=')
        value = value.strip()
        split_key = key.split(".")
        d = header_dict
        if len(split_key) > 1:
            for s in split_key[:-1]:
                if s in d:
                    d = d[s]
                else:
                    d[s] = {}
                    d = d[s]
        d[split_key[-1]] = value
    
    return header_dict


def find_links_in_local_parameters(list_of_all_links, parameter_subset, link_keys, chain):

    for key in parameter_subset:
        copy_chain = chain[:]
        copy_chain.append(key)
        if key in link_keys and key != "date":
            list_of_all_links.append(copy_chain)
        else:
            if isinstance(parameter_subset[key], dict):
                find_links_in_local_parameters(list_of_all_links, parameter_subset[key],
                                               link_keys, copy_chain)


def replace_links(links, local_parameters, shared_parameters):
    for chain in links:
        d = local_parameters
        for key in chain[:-1]:
            d = d[key]
        if debug:
            print(("keys_before = ", d.keys()))
        index = d.pop(chain[-1])['*']
        merge(d, shared_parameters[chain[-1]][index])
        if debug:
            print(("keys_shared = ", shared_parameters[chain[-1]][index].keys()))
            print(("keys_after = ", d.keys()))


# Took this function from stackoverflow's user andrew cooke at thread 
# http://stackoverflow.com/questions/7204805/dictionaries-of-dictionaries-merge .
def merge(a, b, chain=[]):
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], chain + [str(key)])
            elif a[key] == b[key]:
                pass
            else:
                raise Exception("Conflict at %s" % '.'.join(chain + [str(key)]))
        else:
            a[key] = b[key]


def decode_binary_strings(list_of_binary_strings):
    return [b.decode("utf-8") for b in list_of_binary_strings]
