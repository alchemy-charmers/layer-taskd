# taskd Charm 

This charm provides the task sync daemon for the [TaskWarrior][https://taskwarrior.org]

# Usage

`juju deploy cs:~pirate-charmers/taskd`


# Configuration

Several options are present for tuning the certificate generation process, and this charm also supports the
`interface-reverseproxy` reverse proxy relation for running behind a TCP load balancer. The port can be customised, and this
will be passed to the related reverse proxy.
