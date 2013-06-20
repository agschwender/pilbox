class python::pil {
  include python

  package { "libjpeg-dev":
    ensure => installed
  }

  package { [ "libfreetype6", "libfreetype6-dev" ]:
    ensure => installed
  }

  package { "zlib1g-dev":
    ensure => installed
  }

  python::pip { "PIL":
    ensure => installed,
    require => Package[ "libjpeg-dev",
                        "libfreetype6",
                        "libfreetype6-dev",
                        "zlib1g-dev" ]
  }
}
