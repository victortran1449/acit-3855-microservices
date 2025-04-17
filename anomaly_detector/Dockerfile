FROM python:3
LABEL maintainer="vtran57@bcit.ca"
RUN mkdir /app
COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip3 install setuptools
RUN pip3 install -r requirements.txt
COPY . /app
RUN chown -R nobody:nogroup /app
USER nobody
EXPOSE 8130
ENTRYPOINT [ "python3" ]
CMD [ "app.py" ]