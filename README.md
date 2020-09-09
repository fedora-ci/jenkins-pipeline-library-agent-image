# Jenkins JNLP agent for the Fedora CI Jenkins Pipeline Library

This Jenkins agent image contains tools and utilities needed by the Fedora CI Jenkins Pipeline Library.

## Tools

### /usr/bin/tfxunit2junit

This is a simple script which converts TestingFarm XUnit files to the standard JUnit format.

Example usage:

```shell
tfxunit2junit testing_farm_xunit.xml > junit.xml
```

## Development

### Building the container image

Pushing to the master branch will automatically trigger a new container image build in [quay.io](https://quay.io/organization/fedoraci).

The resulting image will have the following name: `quay.io/fedoraci/pipeline-library-agent:prototype`

> **_NOTE:_** We use "prototype" tag now so we can iterate and test changes faster. However, in future, the prototype tag will be replaced with a short commit hash.
