ARG BUILD_FROM
FROM ${BUILD_FROM}

# MieleRESTServer, pinned commit
ARG MRS_COMMIT=6141aab096fcc2e3b6bc219045828f435c9db58a

RUN pip3 install --no-cache-dir cryptography Flask flask_restful PyYAML requests "paho-mqtt>=2,<3" \
 && pip3 install --no-cache-dir --no-deps \
      "https://github.com/akappner/MieleRESTServer/archive/${MRS_COMMIT}.zip"

COPY bridge.py /bridge.py
CMD ["python3", "-u", "/bridge.py"]
