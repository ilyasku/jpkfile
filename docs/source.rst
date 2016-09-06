Source code documentation
=========================

The whole jpkfile project/package consists of only one relevant file for normal use: jpkfile.py.  
It is composed of three classes: :py:class:`~jpkfile.JPKFile`, :py:class:`~jpkfile.JPKSegment`, and :py:class:`~jpkfile.JPKMap`. The user's interface is mostly covered by the :py:class:`~jpkfile.JPKFile` class, which is used for regular force and tweezer recordings. For force maps, you need to use the :py:class:`~jpkfile.JPKMap` class. :py:class:`~jpkfile.JPKSegment` is usually created and populated internally from within the other two classes.  

JPKFile
------- 

.. autoclass:: jpkfile.JPKFile
   :members: get_array, get_info, read_files, parameters, segments, num_segments, has_shared_header, shared_parameters

JPKSegment
----------

.. autoclass:: jpkfile.JPKSegment
   :members: get_info, get_array, get_decoded_data, get_time, parameters, data

JPKMap
------

.. autoclass:: jpkfile.JPKMap
   :members: read_files, get_single_pixel, flat_indices, parameters


Helper functions, attributes and classes
----------------------------------------

.. automodule:: jpkfile
   :members: parse_header_file, extract_data, determine_conversions_automatically, DATA_TYPES, ARCHIVE_TYPES, debug

.. autoclass:: jpkfile._VirtualZipFile
   :members: parent_zip, list_of_filenames, prefix

.. autoclass:: jpkfile._JPKFileForJPKMap
