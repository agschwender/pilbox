Pilbox [![Build Status](https://travis-ci.org/agschwender/pilbox.png)](https://travis-ci.org/agschwender/pilbox) [![Coverage Status](https://coveralls.io/repos/agschwender/pilbox/badge.png)](https://coveralls.io/r/agschwender/pilbox)
======

Pilbox is an image resizing application server built on Python's [Tornado web framework](http://www.tornadoweb.org/en/stable/) using the [Python Imaging Library (Pillow)](https://pypi.python.org/pypi/Pillow/2.1.0). It is not intended to be the primary source of images, but instead acts as a proxy which requests images and resizes them as desired.

Setup
=====

Dependencies
------------

  * >= [Python 2.7](http://www.python.org/download/)
  * [Pillow 2.1.0](https://pypi.python.org/pypi/Pillow/2.1.0)
  * [Tornado 3.1](https://pypi.python.org/pypi/tornado/3.1)
  * [OpenCV 2.x](http://opencv.org/)
  * Image Libraries: libjpeg-dev, libfreetype6, libfreetype6-dev, zlib1g-dev

Vagrant
-------

Packaged with Pilbox is a [Vagrant](http://www.vagrantup.com/) configuration file which installs all necessary dependencies on a virtual box. See the [Vagrant documentation for installation instructions](http://docs.vagrantup.com/v2/installation/). Once installed, the following will start a virtual machine.

    $ vagrant up

To access the virtual machine itself, simply...

    $ vagrant ssh

Running
=======

Manual
------

To run the application, issue the following command

    $ python -m pilbox.app

By default, this will run the application on port 8888 and can be accessed by visiting:

    http://localhost:8888/

To see a list of all available options, run

    $ python -m pilbox.app --help
    Usage: pilbox/app.py [OPTIONS]

    Options:

      --allowed_hosts            list of allowed hosts (default [])
      --background               default hexadecimal bg color (RGB or ARGB)
      --client_key               client key
      --client_name              client name
      --config                   path to configuration file
      --debug                    run in debug mode (default False)
      --filter                   default filter to use when resizing
      --help                     show this help information
      --max_requests             max concurrent requests (default 40)
      --port                     run on the given port (default 8888)
      --position                 default cropping position
      --quality                  default jpeg quality, 0-100
      --timeout                  timeout of requests in seconds (default 10)

Vagrant
-------

When running via Vagrant, the application is automatically started on port 8888 on 192.168.100.100, i.e.

    http://192.168.100.100:8888/

Calling
=======

To use the image resizing service, include the application url as you would any other image. E.g. this image url

```html
<img src="http://i.imgur.com/zZ8XmBA.jpg" />
```

Would be replaced with this image url

```html
<img src="http://localhost:8888/?url=http%3A%2F%2Fi.imgur.com%2FzZ8XmBA.jpg&w=300&h=300&mode=crop" />
```

This will request the image served at the supplied url and resize it to `300x300` using the `crop` mode. The following is the list of parameters that can be supplied to the service

  * _url_: The url of the image to be resized
  * _w_: The desired width of the image
  * _h_: The desired height of the image
  * _mode_: The resizing method: clip, crop (default), fill and scale
    * _clip_: Resize to fit within the desired region, keeping aspect ratio
    * _crop_: Resize so one dimension fits within region, center, cut remaining
    * _fill_: Fills the clipped space with a background color
    * _scale_: Resize to fit within the desired region, ignoring aspect ratio
  * _filter_: The filtering algorithm used for resizing
    * _nearest_: Fastest, but often images appear pixelated
    * _bilinear_: Faster, can produce acceptable results
    * _bicubic_: Fast, can produce acceptable results
    * _antialias_: Slower, produces the best results
  * _bg_: Background color used with fill mode (RGB or ARGB)
    * _RGB_: 3- or 6-digit hexadecimal number
    * _ARGB_: 4- or 8-digit hexadecimal number, only relevant for PNG images
  * _pos_: The crop position
    * _top-left_: Crop from the top left
    * _top_: Crop from the top center
    * _top-right_: Crop from the top right
    * _left_: Crop from the center left
    * _center_: Crop from the center
    * _right_: Crop from the center right
    * _bottom-left_: Crop from the bottom left
    * _bottom_: Crop from the bottom center
    * _bottom-right_: Crop from the bottom right
    * _face_: Identify faces and crop from the midpoint of their position(s)
  * _q_: The quality (1-100) used to save the image, only relevant to JPEGs.
  * _client_: The client name
  * _sig_: The signature

The `url`, and either `w` or `h` parameters are required. If only one dimension is specified, the application will determine the other dimension using the aspect ratio. `mode` is optional and defaults to `crop`. `filter` is optional and defaults to `bicubic`. `bg` is optional and defaults to `fff`. `pos` is optional and defaults to `center`. `q` is optional and defaults to `75`. `client` is required only if the `client_name` is defined within the configuration file. Likewise, `sig` is required only if the `client_key` is defined within the configuration file. See the [signing section](#signing) for details on how to generate the signature.

Examples
========

The following images show the various resizing modes in action for an original image size of `640x428` that is being resized to `500x400`.

Clip
----

The image is resized to fit within a `500x400` box, maintaing aspect ratio and producing an image that is `500x334`. Clipping is useful when no portion of the image can be lost and it is acceptable that the image not be exactly the supplied dimensions, but merely fit within the dimensions.

![Clipped image](pilbox/test/data/expected/example-500x400-clip.jpg)

Crop
----

The image is resized so that one dimension fits within the `500x400` box. It is then centered and the excess is cut from the image. Cropping is useful when the position of the subject is known and the image must be exactly the supplied size.

![Cropped image](pilbox/test/data/expected/example-500x400-crop.jpg)

Fill
----

Similar to clip, fill resizes the image to fit within a `500x400` box. Once clipped, the image is centered within the box and all left over space is filled with the supplied background color. Filling is useful when no portion of the image can be lost and it must be exactly the supplied size.

![Filled image](pilbox/test/data/expected/example-500x400-fill-ccc.jpg)

Scale
-----

The image is clipped to fit within the `500x400` box and then stretched to fill the excess space. Scaling is often not useful in production environments as it generally produces poor quality images. This mode is largely included for completeness.

![Scale image](pilbox/test/data/expected/example-500x400-scale.jpg)

Testing
=======

To run all tests, issue the following command

    $ python -m pilbox.test.runtests

To run individual tests, simply indicate the test to be run, e.g.

    $ python -m pilbox.test.runtests pilbox.test.signature_test

Signing
=======

In order to secure requests so that unknown third parties cannot easily use the resize service, the application can require that requests provide a signature. To enable this feature, set the `client_key` option. The signature is a hexadecimal digest generated from the client key and the query string using the HMAC-SHA1 message authentication code (MAC) algorithm. The below python code provides an example implementation.

```python
import hashlib
import hmac

def derive_signature(key, qs):
    m = hmac.new(key, None, hashlib.sha1)
    m.update(qs)
    return m.hexdigest()
```

The signature is passed to the application by appending the `sig` paramater to the query string; e.g. `x=1&y=2&z=3&sig=c9516346abf62876b6345817dba2f9a0c797ef26`. Note, the application does not include the leading question mark when verifying the supplied signature. To verify your signature implementation, see the `pilbox.signature` command described in the [tools section](#tools).

Configuration
=============

All options that can be supplied to the application via the command line, can also be specified in the configuration file. Configuration files are simply python files that define the options as variables. The below is an example configuration.

    # General settings
    port = 8888

    # Set client name and key if the application requires signed requests. The
    # client must sign the request using the client_key, see README for
    # instructions.
    client_name = "sample"
    client_key = "3NdajqH8mBLokepU4I2Bh6KK84GUf1lzjnuTdskY"

    # Set the allowed hosts as an alternative to signed requests. Only those
    # images which are served from the following hosts will be requested.
    allowed_hosts = ["localhost"]

    # Request-related settings
    max_requests = 50
    timeout = 7.5

    # Set default resizing options
    background = "ccc"
    filter = "bilinear"
    position = "top"
    quality = 90

Tools
=====

To verify that your client application is generating correct signatures, use the signature command.

    $ python -m pilbox.signature --key=abcdef "x=1&y=2&z=3"
    Query String: x=1&y=2&z=3
    Signature: c9516346abf62876b6345817dba2f9a0c797ef26
    Signed Query String: x=1&y=2&z=3&sig=c9516346abf62876b6345817dba2f9a0c797ef26

The application allows the use of the resize functionality via the command line.

    $ python -m pilbox.image --width=300 --height=300 http://i.imgur.com/zZ8XmBA.jpg > /tmp/foo.jpg

If a new mode is added or a modification was made to the libraries that would change the current expected output for tests, run the generate test command to regenerate the expected output for the test cases.

    $ python -m pilbox.test.genexpected

Deploying
=========

The application itself does not include any caching. It is recommended that the application run behind a CDN for larger applications or behind varnish for smaller ones.

Defaults for the application have been optimized for quality rather than performance. If you wish to get higher performance out of the application, it is recommended you use a less computationally expensive filtering algorithm and a lower JPEG quality. For example, add the following to the configuration.

    # Set default resizing options
    filter = "bicubic"
    quality = 75

Changelog
=========

  * 0.1: Image resizing fit
  * 0.1.1: Image cropping
  * 0.1.2: Image scaling
  * 0.2: Configuration integration
  * 0.3: Signature generation
  * 0.3.1: Signature command-line tool
  * 0.4: Image resize command-line tool
  * 0.5: Facial recognition cropping
  * 0.6: Fill resizing mode
  * 0.7: Resize using crop position
  * 0.7.1: Resize using a single dimension, maintaining aspect ratio
  * 0.7.2: Added filter and quality options
  * 0.7.3: Support python 3
  * 0.7.4: Fixed cli for image generation
  * 0.7.5: Write output in 16K blocks
  * 0.8: Added support for ARGB (alpha-channel)
  * 0.8.1: Increased max clients and write block sizes
  * 0.8.2: Added configuration for max clients and timeout
  * 0.8.3: Only allow http and https protocols

TODO
====

  * How to reconcile unavailable color profiles?
  * Add backends (S3, file system, etc...) if necessary
