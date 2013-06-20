Exec {
  path => [ "/usr/local/bin", "/usr/bin", "/bin" ]
}

node default {
  include python
  include python::pil

  python::pip { "tornado": ensure => installed }

  package { "nginx": ensure => installed }
}
