class python {
  package {
    "python": ensure => installed;
    "python-dev": ensure => installed;
    "python-setuptools": ensure => installed;
    "python-pip": ensure => installed;
  }

  define pip($ensure = installed) {
    case $ensure {
      installed: {
        exec { "pip install $name": }
      }
      latest: {
        exec { "pip install --upgrade $name": }
      }
      default: {
        exec { "pip install $name==$ensure": }
      }
    }
  }
}
