FROM registry.centos.org/centos/centos:8
LABEL maintainer "Fedora CI"
LABEL description="Jenkins Agent for the Fedora CI Jenkins Pipeline Library"

ENV SCRIPTS_DIR=/usr/local/libexec/ci-scripts
ENV WORKSPACE_DIR=/workspace

RUN mkdir -p ${SCRIPTS_DIR} &&\
    chmod 777 ${SCRIPTS_DIR}

RUN yum -y install epel-release

RUN yum -y install \
    koji \
    python3-pip \
    fedpkg \
    python2-docutils \
    git \
    rpm-build \
    && yum clean all

ADD requirements.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt

ADD scripts/tfxunit2junit.py ${SCRIPTS_DIR}
ADD scripts/pullRequest2scratchBuild.sh ${SCRIPTS_DIR}

RUN ln -s ${SCRIPTS_DIR}/tfxunit2junit.py /usr/local/bin/tfxunit2junit
RUN ln -s ${SCRIPTS_DIR}/pullRequest2scratchBuild.sh /usr/local/bin/pullRequest2scratchBuild.sh

WORKDIR ${WORKSPACE_DIR}
