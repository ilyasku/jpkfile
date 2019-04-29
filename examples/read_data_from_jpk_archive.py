# coding: utf-8

# ich war hier mal drin (bg)

# ## Load the module
# If you added the folder in which `jpkfile.py` is to you site-packages, you should be able to import the module.

import jpkfile


# ## Create a JPKFile object

jpk = jpkfile.JPKFile("../examples/force-save-2016.06.15-13.17.08.jpk-force")


# ## Structure of JPKFile objects

# * Data is separated in segments in jpk archives. Thus, it is separated in JPKFile objects as well. The member JPKFile.segments is a list of JPKSegment objects.

jpk.segments


# * To get some basic information on the jpk archive behind the JPKFile object, you can use the JPKFile.get_info function. Note that 'segments' is currently the only working keyword here ...

print(jpk.get_info('segments'))


# ## Data of segments
# The JPKSegment objects contain some information and parameters as well. Additionaly, they contain the segment's data. 

# JPKSegment.data is a dictionary, where keys are different channels and values are data arrays and parameters on how to convert the raw data to physical values.  
# To figure out what the names of valid channels are, print JPKSegment.data.keys().

s0 = jpk.segments[0]
print(s0.data.keys())


# ## Extract data converted to physical values
# Use the function get_array() to get the physical data of channels.  
# Let's say you want data of channel 'height' and 'vDeflection' (which makes sense for the example file, it looks like all the other channels are not relevant, since there are no parameters on conversion to physical values defined; jpk appears to always store all channels that could be used for the method of recording) you need to provide these channel names as first parameter in a list.


s0_data, s0_units = s0.get_array(['height','vDeflection'])


print(s0_data)


# The function returns a tuple with a labeled numpy array as first item, a dictionary specifying the physical units for each channel.

print(s0_units)


# ## Data of all segments
# You can also retrieve the data of all segments in a similar way, by using JPKFile's get_array function.

data,units = jpk.get_array(['height','vDeflection'])


# ## But for plotting ...
# it is probably more useful to extract them separately, to be able to plot them separately.

s1_data = jpk.segments[1].get_array(['height','vDeflection'])[0]
s2_data = jpk.segments[2].get_array(['height','vDeflection'])[0]
# I actually don't know what the last segment is, it contains only 2 data points


# ## Plot the data

import matplotlib.pyplot as plt
f,ax = plt.subplots(1,1)

ax.plot(s0_data['height'],s0_data['vDeflection'], label = jpk.segments[0].get_info('type'))
ax.plot(s1_data['height'],s1_data['vDeflection'], label = jpk.segments[1].get_info('type'))
ax.plot(s2_data['height'],s2_data['vDeflection'], label = jpk.segments[2].get_info('type'))
ax.legend()

ax.set_xlabel('height [%s]' % s0_units['height'])
ax.set_ylabel('vDeflection [%s]' % s0_units['vDeflection'])

f.show()



