# BOS-mint

![](https://img.shields.io/pypi/v/bos-mint.svg?style=for-the-badge)
![](https://img.shields.io/github/downloads/pbsa/bos-mint/total.svg?style=for-the-badge)
![](https://img.shields.io/pypi/pyversions/bos-mint.svg?style=for-the-badge)

[![docs master](https://readthedocs.org/projects/bos-mint/badge/?version=latest)](http://bos-mint.rtfd.io/en/latest/)
[![docs develop](https://readthedocs.org/projects/bos-mint/badge/?version=develop)](http://bos-mint.rtfd.io/en/develop/)

The Manual Intervention Module (MINT) is one of two services that are required for proper operation of Bookie Oracle Software(BOS). MINT provides a web interface for Witnesses to manually intervene in the otherwise fully-automated process of bringing Bookie Events, BMGs, and Betting Markets to the Peerplays blockchain (through [`bos-auto`](https://github.com/PBSA/bos-auto)). This allows Witnesses to handle any edge cases that may arise and cannot be dealt with by bos-auto.

## Documentation
For directions on how to install and run `bos-mint` please visit our [documentation page](http://bos-mint.readthedocs.io/en/master/installation.html).

## Development use
Checkout the repository and run

```bash
$ ./run_dev_server.sh    # Run MINT
```
