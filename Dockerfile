FROM registry.fedoraproject.org/fedora:34
LABEL maintainer "Fedora CI"
LABEL description="Jenkins Agent for the Fedora CI Jenkins Pipeline Library"

ENV SCRIPTS_DIR=/usr/local/libexec/ci-scripts
ENV WORKSPACE_DIR=/workspace

RUN mkdir -p ${SCRIPTS_DIR} ${WORKSPACE_DIR} && \
    chmod 777 ${SCRIPTS_DIR} ${WORKSPACE_DIR}

RUN dnf -y install \
    koji \
    python3-pip \
    fedpkg \
    git \
    rpm-build \
    && dnf clean all

ADD config/brewkoji.conf /etc/koji.conf.d/

ADD requirements.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt

ADD scripts/tfxunit2junit.py ${SCRIPTS_DIR}
ADD scripts/pullRequest2scratchBuild.sh ${SCRIPTS_DIR}
ADD scripts/scratch.sh ${SCRIPTS_DIR}

RUN ln -s ${SCRIPTS_DIR}/tfxunit2junit.py /usr/local/bin/tfxunit2junit
RUN ln -s ${SCRIPTS_DIR}/pullRequest2scratchBuild.sh /usr/local/bin/pullRequest2scratchBuild.sh
RUN ln -s ${SCRIPTS_DIR}/scratch.sh /usr/local/bin/scratch.sh

WORKDIR ${WORKSPACE_DIR}
