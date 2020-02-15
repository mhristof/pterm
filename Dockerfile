FROM python:3.7
MAINTAINER Mike Christof <mhristof@gmail.com>


ADD requirements.txt /
RUN pip install -r /requirements.txt
RUN pip install pytest
ADD . /work
RUN pip install /work
CMD pytest /work
