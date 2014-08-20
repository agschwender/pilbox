#!/usr/bin/env python
#
# Copyright 2013 Adam Gschwender
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Pilbox server and tools

Versions:

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
  * 0.8.4: Added support for WebP
  * 0.8.5: Added format option and configuration for mode and format
  * 0.8.6: Added custom position support
  * 0.9: Added rotate operation
  * 0.9.1: Added sub-region selection operation
  * 0.9.4: Added Pilbox as a PyPI package
  * 0.9.10: Converted README to reStructuredText
  * 0.9.14: Added Sphinx docs
  * 0.9.15: Added implicit base url
  * 0.9.16: Added validate cert to configuration
  * 0.9.17: Added support for GIF format
  * 0.9.18: Fix for travis builds on python 2.6 and 3.3
  * 0.9.19: Validate cert fix
  * 0.9.20: Added optimize option
  * 0.9.21: Added console script entry point
  * 1.0.0: Modified for easier library usage
  * 1.0.1: Added allowed operations and default operation
"""

# human-readable version number
version = "1.0.1"

# The first three numbers are the components of the version number.
# The fourth is zero for an official release, positive for a development
# branch, or negative for a release candidate or beta (after the base version
# number has been incremented)
version_info = (1, 0, 1, 0)
