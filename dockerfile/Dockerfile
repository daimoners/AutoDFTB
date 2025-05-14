################################################################
# AUTODFTB Software Containerized
# Creator: Mario Vozza & Tommaso Forni
# Institution: Politecnico di Torino, DAIMON CNR
# Email: mario.vozza@polito.it; tommaso.forni@polito.it
# Description: This Dockerfile sets up a containerized environment
# for the AUTODFTB software.
# ###############################################################


FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive


COPY dftbplus.zip /usr/local/dftbplus.zip

# ###############################################################
# Install System Tools and Dependencies
# ###############################################################
RUN apt-get update && apt-get install -y \
    wget bzip2 ca-certificates curl git zip \
    build-essential

RUN unzip /usr/local/dftbplus.zip -d /usr/local && \
    rm /usr/local/dftbplus.zip


WORKDIR /applications
COPY requirements.txt /applications/requirements.txt
COPY auto_dftb.py /applications/auto_dftb.py
COPY auto_optimize_geometry.py /applications/auto_optimize_geometry.py
COPY auto_stm.py /applications/auto_stm.py
COPY auto_transport.py /applications/auto_transport.py

# ###############################################################
# Install Miniconda
# ###############################################################

RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh && \
    bash ~/miniconda.sh -b -p $CONDA_DIR && \
    rm ~/miniconda.sh && \
    $CONDA_DIR/bin/conda clean -afy
    
RUN 