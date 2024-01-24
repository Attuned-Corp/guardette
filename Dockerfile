FROM public.ecr.aws/lambda/python:3.11

COPY ./src/guardette ${LAMBDA_TASK_ROOT}/src/guardette
COPY pyproject.toml ${LAMBDA_TASK_ROOT}
RUN pip install .

COPY main.py ${LAMBDA_TASK_ROOT}
COPY ./.guardette/policy.yml ${LAMBDA_TASK_ROOT}/.guardette/policy.yml

CMD [ "main.handler" ]
