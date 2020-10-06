FROM openshift/jenkins-slave-base-centos7:v3.11
LABEL maintainer "Fedora CI"
LABEL description="Jenkins JNLP agent for the Fedora CI Jenkins Pipeline Library"

ENV TOOLS_DIR=/tools/

RUN mkdir -p ${TOOLS_DIR} &&\
    chmod 777 ${TOOLS_DIR}

RUN yum -y install \
    koji \
    python3-pip \
    fedpkg \
    git \
    rpm-build \
    && yum clean all

ADD requirements.txt /tmp/
ADD tfxunit2junit.py ${TOOLS_DIR}

RUN pip3 install -r /tmp/requirements.txt

RUN ln -s ${TOOLS_DIR}/tfxunit2junit.py /usr/bin/tfxunit2junit
