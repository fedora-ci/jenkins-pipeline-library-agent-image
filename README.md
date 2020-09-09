# Jenkins JNLP agent for the Fedora CI Jenkins Pipeline Library

This Jenkins agent image contains tools and utilities needed by the Fedora CI Jenkins Pipeline Library.

## Tools

### /usr/bin/tfxunit2junit

This is a simple script which converts TestingFarm XUnit files to the standard JUnit format.

Example usage:

```shell
tfxunit2junit testing_farm_xunit.xml > junit.xml
```
