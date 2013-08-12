class python {
  package {
    "python": ensure => installed;
    "python-software-properties": ensure => installed;
    "python-dev": ensure => installed;
    "python-setuptools": ensure => installed;
    "python-pip": ensure => installed;
  }

  define pip($ensure = installed) {
    case $ensure {
      installed: {
        exec { "pip install $name":
          require => Package[ "python-pip" ],
          tries => 3,
          try_sleep => 15,
        }
      }
      latest: {
        exec { "pip install --upgrade $name":
          require => Package[ "python-pip" ],
          tries => 3,
          try_sleep => 15,
        }
      }
      default: {
        exec { "pip install $name==$ensure":
          require => Package[ "python-pip" ],
          tries => 3,
          try_sleep => 15,
        }
      }
    }
  }
}
