FROM python:3.13.2-slim
LABEL maintainer="vtran57@bcit.ca"
RUN mkdir /app
COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip3 install setuptools
RUN pip3 install -r requirements.txt
COPY . /app
RUN chown -R nobody:nogroup /app
USER nobody
EXPOSE 8090
ENTRYPOINT [ "python3" ]
CMD [ "app.py" ]