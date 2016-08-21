from struct import unpack
from zipfile import ZipFile
from dateutil import parser
import sys
import numpy as np

## Dictionary assigning item length (in .dat files) and struckt.unpack abbreviation
# to the keys used in header files (.properties).
DATA_TYPES = {'short':(2,'h'),'unsignedshort':(2,'H'),
              'integer-data':(4,'i'), 'signedinteger':(4,'i'),
              'float-data':(4,'f')}

DEFAULT_CONVERSION_CHAIN = {'height': ('nominal',),
                            'vDeflection' : ('distance','force'),
                            'hDeflection' : (),
                            'strainGaugeHeight' : (),
                            'error':(),
                            'xSignal1':()}

ARCHIVE_TYPES = {"simple-force-scan-series-header":'force',
                 "nt-force-scan-series-header": 'nt-force'}


debug = False

class JPKFile:

    def __init__(self,fname):
        

        self._zip = ZipFile(fname)
        self.data = None
        self.parameters = {}
        self.num_segments = 0
        self.segments = {}
        self.archive_type = ""
        self.has_shared_header = False
        self.shared_parameters = None

        self.read_files()

    def read_files(self):
        
        top_header = self._zip.filelist[0].filename
        top_header_f = self._zip.open(top_header)
        top_header_content = top_header_f.readlines()
        
        self.parameters.update(parse_header_file(top_header_content))

        self.archive_type = ARCHIVE_TYPES[self.parameters['force-scan-series']['header']['type']]

        list_of_filenames = [f.filename for f in self._zip.filelist]

        if list_of_filenames.count("shared-data/header.properties"):
            self.has_shared_header = True
            self.shared_parameters = {}
            shared_header = self._zip.filelist.pop(list_of_filenames.index("shared-data/header.properties"))
            shared_header_f = self._zip.open(shared_header)
            shared_header_content = shared_header_f.readlines()

            self.shared_parameters.update(parse_header_file(shared_header_content))



        for zip_f in self._zip.filelist[1:]:
            fname = zip_f.filename
            
            split = fname.split("/")

            if split[0] == "segments":
                if len(split)<3:
                    pass
                else:
                    segment = int(split[1])

                    if segment>self.num_segments-1:
                        new_JPKSegment = JPKSegment(self.has_shared_header, self.shared_parameters)
                        new_JPKSegment.index = segment
                        self.segments[segment] = new_JPKSegment
                        self.num_segments += 1
                        
                    if len(split) == 3 and split[2] == "segment-header.properties":
                        header_f = self._zip.open(fname)
                        header_content = header_f.readlines()
                        self.segments[segment].parameters = parse_header_file(header_content)
                        #self.data['t'] = np.linspace(0.0,float(self.segments[segment].parameters['force-segment-header']['duration']), int(self.segments[segment].parameters['force-segment-header']['num-points']))
                        self.segments[segment].data['t'] = np.arange(0.0,float(self.segments[segment].parameters['force-segment-header']['duration']), float(self.segments[segment].parameters['force-segment-header']['duration'])/float(self.segments[segment].parameters['force-segment-header']['num-points']))
                    
                    elif len(split) == 4 and split[3][-4:] == ".dat":

                        channel_label = split[3][:-4]
                        data_f = self._zip.open(fname)
                        content = data_f.read()

                        if debug:
                            print segment, channel_label

                        shared = False
                        if self.has_shared_header:
                            if self.segments[segment].parameters['channel'][channel_label].keys().count('lcd-info'):
                                shared = True

                        #if self.archive_type == 'force':
                        if not shared:

                            if debug:
                                print "NOT SHARED" 


                            dtype = self.segments[segment].parameters['channel'][channel_label]['data']['type']

                            encoder_parameters = None
                            if self.segments[segment].parameters['channel'][channel_label].keys().count('data'):
                                if self.segments[segment].parameters['channel'][channel_label]['data'].keys().count('encoder'):
                                    encoder_parameters = self.segments[segment].parameters['channel'][channel_label]['data']['encoder']

                            conversion_parameters = None
                            if self.segments[segment].parameters['channel'][channel_label].keys().count('conversion-set'):
                                if self.segments[segment].parameters['channel'][channel_label]['conversion-set'].keys().count('conversion'):
                                    conversion_parameters = self.segments[segment].parameters['channel'][channel_label]['conversion-set']

                            if not encoder_parameters:
                                sys.stderr.write("WARNING! Did not find encoder parameters!\n")

                            if not conversion_parameters:
                                sys.stderr.write("WARNING! Did not find conversion parameters!\n")
                        
                        else:
                            if debug:
                                print "SHARED"

                            shared_parameters_index = self.segments[segment].parameters['channel'][channel_label]['lcd-info']['*']
                            shared_parameters = self.shared_parameters['lcd-info'][shared_parameters_index]

                            dtype = shared_parameters['type']
                            

                            encoder_parameters = None
                            if shared_parameters.keys().count('encoder'):
                                encoder_parameters = shared_parameters['encoder']
                                
                            conversion_parameters = None
                            if shared_parameters.keys().count('conversion-set'):
                                if shared_parameters['conversion-set'].keys().count('conversion'):
                                    conversion_parameters = shared_parameters['conversion-set']

                            if not encoder_parameters:
                                sys.stderr.write("WARNING! Did not find encoder parameters!\n")

                            if not conversion_parameters:
                                sys.stderr.write("WARNING! Did not find conversion parameters!\n")
                            
                        num_points = int(self.segments[segment].parameters['force-segment-header']['num-points'])
                            
                        data = extract_data(content, dtype, num_points)
                        self.segments[segment].data[channel_label] = (data , {'encoder_parameters': encoder_parameters, 'conversion_parameters': conversion_parameters})
                                                    
                
            else:
                sys.stderr.write("ERROR! Encountered new folder '%s'.\nDo not know how to handle that.")
                sys.exit(1)
            
    def get_array(self, channels = [], decode = True):
        data, units = self.segments[0].get_array(channels, decode)
        for i in range(1,len(self.segments)):
            s = self.segments[i]
            d, u = s.get_array(channels, decode)
            if u == units:
                data = np.concatenate((data,d))
            else:
                msg = "ERROR in JPKFile.get_array!\nCould not concatenate data of all segments: units not matching\n"
                sys.stderr.write(msg)
                sys.exit(1)
        return data, units

    def get_info(self, issue = 'general'):
        if issue == 'segments':
            s = ""
            s = s + "=" * 70 + "\n"
            s = s + "SEGMENT\tTYPE\tNUM POINTS\tDURATION\n"
            s = s + "-------\t----\t----------\t--------\n"            
            for i in range(len(self.segments)):
                s = s + str(i) + "\t" + self.segments[i].get_info('type') + "\t" + \
                    self.segments[i].get_info('num-points') + '\t\t' + self.segments[i].get_info('duration')+ '\n'
            s = s + "=" * 70 + "\n"
            #s = s + "SEGMENT\tNUMBER OF POINTS\n"
            #s = s + "-------\t----------------\n"
            #for i in range(len(self.segments)):
            #s = s + str(i) + "\t" + self.segments[i].get_info('type') + '\n'
            
        return s
                

        

class JPKSegment:

    def __init__(self, parent_has_shared_header = False, shared_properties = None):
        
        self.parameters = {}
        self.data = {}
        self.index = None
        self.parent_has_shared_header = parent_has_shared_header
        self.shared_properties = shared_properties


    def get_time(self, offset = 0):
        return self.data['t']+offset

    def get_array(self, channels = [], decode = True):
        _data = {}
        dtypes = []
        shape = self.data[channels[0]][0].shape
        units = {}
        for c in channels:
            #try:
            if decode:
                d,unit = self.get_decoded_data(c)
            
            else:
                d,unit = (self.data[c][0],'digital')

            if d.shape[0] != shape[0]:
                sys.stderr.write("ERROR! Number of points in data channel '%s' does not match expected number of %i\n" % (c,shape[0]))
                sys.exit(1)
            _data[c] = d
            dtypes.append((c,d.dtype))
            units[c] = unit
        A = np.zeros(shape, dtype = dtypes)
        for c in channels:
            A[c] = _data[c]
        return A, units
        


    def get_decoded_data(self,channel, conversions_to_be_applied = 'auto'):

        unit = 'digital'

        encoder_parameters = self.data[channel][1]['encoder_parameters']
        conversion_parameters = self.data[channel][1]['conversion_parameters']['conversion']
        data = self.data[channel][0]

        raw = data[:]
        if encoder_parameters:
            if encoder_parameters['scaling']['style'] == 'offsetmultiplier':
                multiplier_raw = float(encoder_parameters['scaling']['multiplier'])
                offset_raw = float(encoder_parameters['scaling']['offset'])
                raw = multiplier_raw * raw + offset_raw

                unit = encoder_parameters['scaling']['unit']['unit']
            else:
                sys.stderr.write("ERROR! Can only handle converters of type 'offsetmultiplier' so far.")
                sys.exit(1)

        else:
            sys.stderr.write("WARNING! No encoder parameters found for channel '%s'.\n" % channel)


        if type(conversions_to_be_applied) == str:
            if conversions_to_be_applied == 'default':
                conversions_to_be_applied = DEAULT_CONVERSION_CHAIN[channel]
                if len(conversions_to_be_applied) == 0:
                    msg = """WARNING! You request decoding of a channel for which no
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
                    sys.stderr.write(msg)
            elif conversions_to_be_applied == 'auto':
                conversions_to_be_applied = determine_conversions_automatically(self.data[channel][1]['conversion_parameters'])
            else:
                sys.stderr.write("WARNING! Unknown string '%s' for function JPKFile.get_decoded_data's parameter conversions_to_be_applied.\nValid strings: 'auto' and 'default'.\nWill now use 'auto'.\n")
                conversions_to_be_applied = determine_conversions_automatically(self.data[channel][1]['conversion_parameters'])

        if conversion_parameters:

            conversion_keys = conversion_parameters.keys()
            for c in conversions_to_be_applied:

                if not conversion_keys.count(c):
                    sys.stderr.write("ERROR! Requested conversion '%s' can't be applied,\nno parameters for '%s' found in jpk header." % (c,c))
                    sys.exit(1)
                    return
                else:
                    if conversion_parameters[c]['defined'] == 'false':
                        sys.stderr.write("ERROR! Requested conversion '%s' can't be applied!\nThis conversion was specified as not defined\nin jpk header file." % c)
                        sys.exit(1)
                        return


            if debug:
                print("="*70)
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
                    sys.stderr.write("ERROR! Can only handle converters of type 'offsetmultiplier' so far.")
                    sys.exit(1)
        else:
            sys.stderr.write("WARNING! No conversion parameters found for channel '%s'.\n" % channel)
                        
        return raw,unit

    def get_info(self, issue = 'general'):
        """
        Request information (string) on some issue.
        This is basically just a more user-friendly assignment of
        parameters of interest to single keywords.
        For the 'issue' parameter the following strings are valid:
            * 'general' (default)
            * 'channels'
            * 'num-points'
            * 'duration'
            * 'type'
        @param issue Keyword specifying what kind of information is asked for.
        @return string or list of strings.
        """
        d = {'channels': self.parameters['channels']['list'],
             'num-points': self.parameters['force-segment-header']['num-points'],
             'duration': self.parameters['force-segment-header']['duration'],
             'type': self.parameters['force-segment-header']['settings']['style']}
    
        if not issue == 'general':
            return d[issue]
        else:
            s = "="*70 + "\n"
            s = s +" " *10 + "GENERAL INFORMATION ON SEGMENT WITH INDEX "+str(self.index) + "\n"
            s = s + "="*70 + "\n"
            s = s + "Type of segment:\n"+ " " * 4 + self.get_info('type') + "\n"
            s = s + "List of channels:\n"+ " " * 4 + self.get_info('channels') + "\n"
            s = s + "Each of those channels should contain " + self.get_info('num-points') + " data points,\n" +" " * 4 + "recorded in "+ self.get_info('duration') + " seconds (OR WHAT IS UNIT OF TIME?)" + "\n"
            s = s + "=" * 70 + "\n"
            return s
            
            

def determine_conversions_automatically(conversion_set_dictionary):

    conversions = [conversion_set_dictionary['conversions']['default']]
    raw_name = conversion_set_dictionary['conversions']['base']
    
    list_of_defined_conversions = conversion_set_dictionary['conversions']['list'].split()


    chain_complete = False
    while not chain_complete:
        key = conversions[-1]
        previous_conversion = conversion_set_dictionary['conversion'][key]['base-calibration-slot']
        if previous_conversion == raw_name:
            chain_complete = True
        else:
            conversions.append(previous_conversion)
    
    conversions.reverse()
    return conversions


def extract_data(content, dtype, num_points):
    point_length, type_code = DATA_TYPES[dtype]

    data = []
    
    for i in range(int(len(content) / point_length)):
        data.append(unpack('!'+type_code, content[i * point_length:(i+1) * point_length]))

    if len(data) == num_points:
        return np.array(data)
    else:
        sys.stderror.write("ERROR! Number of extracted data points is %i, and does not match the number of present data points %i as read from the segment's header file." % (len(data), num_points))
        sys.exit(1)

def parse_header_file(content):
    header_dict = {}

    start = 0
    
    if content[start][:2] == "##":
        start = 1
    
    try:
        from pytz import utc
        fmt = '%Y-%m-%d %H:%M:%S %Z%z'
        t = utc.localize(parser.parse(content[start][1:], dayfirst=True)).strftime(fmt)
    except:
        t = parser.parse(content[start][1:])

    header_dict['date'] = t


    for line in content[start+1:]:
        key,value = line.split("=")
        value = value.strip()
        split_key = key.split(".")
        d = header_dict
        if len(split_key) > 1:
            for s in split_key[:-1]:
                if d.keys().count(s):
                    d = d[s]
                else:
                    d[s] = {}
                    d = d[s]
        d[split_key[-1]] = value
    
    return header_dict


def print_table(content, col_labels = [], row_labels = [], 
                min_col_space = 0, col_sep_character = '|', row_sep_character = '-', 
                header_sep_character = "=", max_cell_width = 30):
    """
    To print some information (e.g. in case JPKFile.get_info( issue = 'segments' ))
    in a nicely formatted table.
    """

    ## check size
    n_rows = len(content)
    n_cols = len(content[0])
    for row in content:
        if len(row)!=n_cols:
            msg = "ERROR in print_table! Number columns per row not identical."
            sys.stderr.write(msg)
            sys.exit(1)


    ## compute number of characters per column/row
    # and format content to match max_cell_width 
    # if necessary
    characters_row = np.ones(n_rows, np.int)
    characters_col = np.zeros(n_cols, np.int)
    formatted_content = []

    for r in range(n_rows):
        formatted_row = []
        size_row = characters_row[r]
        for c in range(n_cols):
            entry = []
            size_col = characters_col[c]
            entry = content[r][c]
            lines = entry.split('\n')
            for l in lines:
                length = len(l)
                if length > max_cell_width:
                    size_col = max_cell_width
                    for i in range(int(length/max_cell_width)):
                        entry.append(l[i*max_cell_width:(i+1)*max_cell_width])
                    if length % max_cell_width:
                        entry.append(l[(i+1)*max_cell_width:])
                else:
                    entry.append(l)
                    if l > size_col:
                        size_col = l
            characters_col[c] = size_col
            if len(entry)>size_row:
                size_row = len(entry)
            formatted_row.append(entry)
        formatted_content.append(formatted_row)
        characters_row[r] = size_row
        
        ## need to take into account size of the labels/headers

        # ... nothing here yet ... 


        ## compose string
        content_string = ""
            

        return content_string
