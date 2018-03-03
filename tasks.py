import os
from invoke import task

@task
def clean(ctx):
    '''Remove build artifacts'''
    ctx.run('rm -rf .cache build snarf.egg-info .coverage htmlcov')


@task
def develop(ctx):
    '''Install development requirements'''
    ctx.run('pip install -U pip', pty=True)
    ctx.run('pip install -e .', pty=True)
    ctx.run('pip install -r requirements.txt', pty=True)


@task
def test(ctx):
    '''Run tests and coverage'''
    ctx.run(
        "py.test --cov-config .coveragerc --cov-report html --cov-report term --cov=snarf",
        pty=True
    )


@task
def cov(ctx):
    '''Open the coverage reports'''
    if os.path.exists('htmlcov/index.html'):
        ctx.run('open htmlcov/index.html', pty=True)

