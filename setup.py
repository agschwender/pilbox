import os.path

from setuptools import setup, Command


with open('README.rst') as f:
    readme = f.read()


class PilboxTest(Command):
    user_options=[]
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        import sys,subprocess
        errno = subprocess.call(
            [sys.executable, os.path.join('pilbox', 'test', 'runtests.py')])
        raise SystemExit(errno)


setup(name='pilbox',
      version='1.0.0',
      description='Pilbox is an image resizing application server built on the Tornado web framework using the Pillow Imaging Library',
      long_description=readme,
      classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        ],
      url='https://github.com/agschwender/pilbox',
      author='Adam Gschwender',
      author_email='adam.gschwender@gmail.com',
      license='http://www.apache.org/licenses/LICENSE-2.0',
      include_package_data=True,
      packages=['pilbox'],
      package_data={
        'pilbox': ['frontalface.xml'],
        },
      install_requires=[
        'tornado==3.2.1',
        'Pillow==2.4.0',
        'sphinx-me==0.2.1',
        ],
      zip_safe=True,
      cmdclass={'test': PilboxTest},
      entry_points = {'console_scripts': ['pilbox = pilbox.app:main']}
      )
