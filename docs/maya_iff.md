Overview
========

The Maya Binary file format is based on EA's [Interchange File Format](http://www.martinreddy.net/gfx/2d/IFF.txt), or IFF.

A notable shortcoming of the original specification is that data lengths are given by 4-byte signed integers. In order to support data larger than 2 GB, Maya 2014 introduces a 64-bit version of its binary scene format.


## A word about alignment

The EA IFF specification requires all chunks to be aligned to even-numbered byte offsets relative to the beginning of the file. Because the data length specified in a chunk header does not include this padding, it must be taken into account while iterating over the contents of e.g. FORM and LIST chunks.

In addition to this basic requirement, Maya's IFF format supports 4- and 8-byte aligned chunks. To this end, custom variants of the FORM and and LIST chunk types are used, called FOR4/FOR8 and LIS4/LIS8, respectively (although FOR1-FOR9 and LIS1-LIS9 are reserved in the spec, it's unclear that Maya's usage is standard).

Maya's 4-byte-aligned variant shares an imporant property with the 2-byte-aligned EA specification. Because chunk type ids, lengths and FORM types are all represented by 4-byte words -- evenly divisible by the desired alignment -- it makes little difference what base offset is used to align data. Whether the end of each chunk is aligned relative to the beginning of the file, the beggining of the chunk, the beginning of the chunk's data, or after the FORM type, the resulting alignment will always be exactly the same.

This property hid a quirk of Maya's IFF parser that is exposed in the 8-byte variant. In this format, chunk type ids and lengths occupy 8 bytes, while FORM types occupy only 4. Additionally, it turns out that alignment is computed relative to the current offset _after_ a 4-byte FORM type (if applicable) is read from the stream. This means that although data is 8-byte aligned in a sense, chunks can begin at offsets within the file that are not a multiple of this alignment. Because of this, FOR8 and LIS8 chunks must be treated specially when iterating of the contents of a file (this also seems to diminish a major benefit of IFF: Being able to skip data without knowing the semantics of its chunk type).


## Additional note on Maya 2014 support

Although Maya's newer binary format uses 8-byte chunk type ids, it mostly uses the same or similar 4-byte ids padded on the _right_. Because the original 4-byte ID now occupies the most-significant bytes of the 8-byte field, care should be taken if treating ids as integer values.


Basic Structure
===============

    FORM Maya
        FORM HEAD
            <Header Fields>
        <File References>
        <Nodes>
        <Connections>


Header Fields
=============

    VERS
        char[] version-name

Specifies the version of Maya that saved the file. This is an ASCII(?) encoded string, although it is not necessarily null terminated (the length of the string is equal to the chunk size).

This is analogous to the `requires maya` command used by Maya ASCII files.

    PLUG
        char[] plugin-name
        char NULL
        char[] plugin-version
        char NULL

Denotes a plugin requirement for the scene file. The contents of this chunk are two null-terminated strings. The first indicates the name of the plugin, and the second indicates the version of the plugin that what used when saving the scene.

This is analogous to the `requires` command used by Maya ASCII files.

    FINF
        char[] key
        char NULL
        char[] value
        char NULL

Stores file metadata.  The contents of this chunk are two null-terminated strings. The first indicates the key or name of the current metadata entry, and the second is its value. Scene metadata typically includes the application name/version, cut identifier and operating system, but can additionally include custom data stored in the scene by the user.

This is a analogous to the `fileInfo` command used by Maya ASCII files.

    AUNI, LUNI and TUNI
        char[] unit-name

Sets the scene's angular, linear and time units, respectively. This is a non-null-terminated ASCII string (the length of the string is equal to the chunk size).

Combined, these header fields are analogous to the `currentUnit` command used by Maya ASCII files.


File References
===============

TODO


Nodes
=====

Node chunks come in 2 flavors. In the first case, a node is created and all non-default attribute values are set. In the second, a builtin node (e.g. "time1") is _selected_, and its attribute values are set. The reason for the distinction is because in the latter case, the node exists by default and does not need to be explicitly created. Still, we "select" it in order to provide context for the attribute values that follow.

Case 1: Create

    FORM <MTypeId>
        CREA
            char flags
            char[] node-name
            char NULL
            optional (char[] parent-name
                      char NULL)
        <Flags>
        <Attributes>

The first byte in the CREA chunk is most likely a set of flags relating to the creation of the node.

Following next is a null-terminated ASCII string specifying the node name. If the node is a DAG node and has a parent, this will be followed by the null-terminated parent node name.


Case 2: Select

    FORM SLCT
        SLCT
            char[] node-name
        <Flags>
        <Attributes>

The nested SLCT chunk (not to be confused with the parent SLCT FORM) contains the node name as a non-null-terminated ASCII string (the length of the string is equal to the chunk size). The rest of the FORM is the same as in the case of node creation.


Flags
=====

TODO


Attributes
==========

TODO


Additional Resources
====================

http://www.martinreddy.net/gfx/2d/IFF.txt
https://courses.cs.washington.edu/courses/cse459/06wi/help/mayaguide/Reference/FileFormats.pdf
http://www.autodesk.com/techpubs/aliasstudio/2009/files/WS73099cc142f4875535a241551166ac8792f-7d72.htm
