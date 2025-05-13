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

RUN apt-get update && apt-get install -y \
    wget bzip2 ca-certificates curl git zip \
    build-essential

RUN unzip /usr/local/dftbplus.zip -d /usr/local && \
    rm /usr/local/dftbplus.zip