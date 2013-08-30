class python::pillow {
  include python

  package { "libjpeg-dev":
    ensure => installed
  }

  package { [ "libfreetype6-dev" ]:
    ensure => installed
  }

  package { "zlib1g-dev":
    ensure => installed
  }

  package { "libwebp-dev":
    ensure => installed
  }

  package { "liblcms1-dev":
    ensure => installed
  }

  python::pip { "Pillow":
    ensure => "2.1.0",
    require => [ Package[ "libjpeg-dev",
                          "libfreetype6-dev",
                          "zlib1g-dev",
                          "libwebp-dev",
                          "liblcms1-dev" ] ]
  }
}
