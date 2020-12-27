FROM python:3.9
WORKDIR /work
COPY dist/nordflux-*.whl ./
RUN pip3 install nordflux-*.whl
RUN rm nordflux-*.whl
CMD ["nordflux"]
