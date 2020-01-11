# -*- coding: utf-8 -*-
import sys
from errno import ENOENT
from os import path, listdir
from argparse import ArgumentParser
from importlib import import_module
from pathlib import Path

from . import dialogs
from . import messages
from . import tkboxes
from .readspec import readspec
from .utils import home, wordjoin, pathjoin, realpath, natsort, p
from .strings import mpiLibs, boolStrings
from .chemistry import readxyz

alias = path.basename(sys.argv[0])
parser = ArgumentParser(add_help=False)
parser.add_argument('--specdir', metavar='SPECDIR', type=str, dest='specdir', required=True, help='Directorio de configuración del trabajo.')
config, remaining = parser.parse_known_args()
specdir = path.expanduser(config.specdir)

hostspec = path.join(specdir, 'hostspec.json')
corespec = path.join(specdir, 'corespec.json')
pathspec = path.join(specdir, 'pathspec.json')
userspec = path.join(home, '.jobspecs', 'jobspec.json')
#TODO: commonspec =

jobconf = readspec(hostspec)
jobconf.merge(readspec(corespec))
jobconf.merge(readspec(pathspec))
if path.isfile(userspec):
    jobconf.merge(readspec(userspec))

scheduler = import_module('.schedulers.' + jobconf.scheduler, package='job2q')

parser = ArgumentParser(prog=alias, description='Ejecuta trabajos de Gaussian, VASP, deMon2k, Orca y DFTB+ en sistemas PBS, LSF y Slurm.')
parser.add_argument('-l', '--list', dest='listoptions', action='store_true', help='Imprimir las versiones de los programas y parámetros disponibles.')
parser.add_argument('-v', '--version', metavar='PROGVERSION', type=str, dest='version', help='Versión del ejecutable.')
parser.add_argument('-q', '--queue', metavar='QUEUENAME', type=str, dest='queue', help='Nombre de la cola requerida.')
parser.add_argument('-n', '--ncore', metavar='#CORES', type=int, dest='ncore', default=1, help='Número de núcleos de cpu requeridos.')
parser.add_argument('-w', '--wait', metavar='TIME', type=float, dest='waitime', help='Tiempo de pausa (en segundos) después de cada ejecución.')
parser.add_argument('-t', '--template', action='store_true', dest='template', help='Interpolar los archivos de entrada.')
parser.add_argument('-j', '--jobname', metavar='MOLNAME', type=str, dest='jobname', help='Nombre del trabajo de interpolación.')
parser.add_argument('-s', '--sort', dest='sort', action='store_true', help='Ordenar la lista de argumentos en orden numérico')
parser.add_argument('-S', '--sortreverse', dest='sortreverse', action='store_true', help='Ordenar la lista de argumentos en orden numérico inverso')
parser.add_argument('-i', '--interactive', dest='interactive', action='store_true', help='Seleccionar interactivamente las versiones y parámetros.')
parser.add_argument('-X', '--xdialog', dest='xdialog', action='store_true', help='Usar Xdialog en vez de la terminal para interactuar con el usuario.')
parser.add_argument('-H', '--here', action='store_true', dest='here', help='Usar la carpeta actual como carpeta de salida')
parser.add_argument('-1', '--single', dest='singlehost', action='store_true', help='Restringe los trabajos MPI para correr en un solo nodo.')
parser.add_argument('--si', '--yes', dest='defaultanswer', action='store_true', default=None, help='Responder "si" a todas las preguntas.')
parser.add_argument('--no', dest='defaultanswer', action='store_false', default=None, help='Responder "no" a todas las preguntas.')
parser.add_argument('--move', dest='move', action='store_true', help='Mover los archivos de entrada a la carpeta de salida en vez de copiarlos.')
parser.add_argument('--scratch', metavar='SCRATCHDIR', type=str, dest='scratch', help='Cambiar el directorio temporal de escritura.')
parser.add_argument('--hosts', metavar='HOSTNAME', type=str, dest='exechosts', help='Solicitar un nodo específico por nombre.')
parser.add_argument('--mol', metavar='MOLFILE', type=str, dest='molfile', help='Ruta del archivo de coordenadas para la interpolación.')
if len(jobconf.parameters) == 1:
    parser.add_argument('-p', metavar='SETNAME', type=str, dest=list(jobconf.parameters)[0], help='Nombre del conjunto de parámetros.')
for key in jobconf.parameters:
    parser.add_argument('--' + key, metavar='SETNAME', type=str, dest=key, help='Nombre del conjunto de parámetros.')
for key in jobconf.formatkeys:
    parser.add_argument('--' + key, metavar='VALUE', type=str, dest=key, help='Valor de la variable de interpolación.')
optconf, remaining = parser.parse_known_args(remaining)

if optconf.listoptions:
    if jobconf.versions:
        messages.listing('Versiones del ejecutable disponibles:', options=sorted(jobconf.versions, key=str.casefold), default=jobconf.defaults.version)
    for key in jobconf.parameters:
        messages.listing('Conjuntos de parámetros disponibles', p(key), options=sorted(listdir(jobconf.parameters[key]), key=str.casefold), default=jobconf.defaults.parameters[key])
    if jobconf.formatkeys:
        messages.listing('Variables de interpolación disponibles:', options=sorted(jobconf.formatkeys, key=str.casefold))
    raise SystemExit()

parser.add_argument('filelist', nargs='+', metavar='FILE(S)', type=str, help='Rutas de los archivos de entrada.')
filelist = parser.parse_args(remaining).filelist

if optconf.waitime is None:
    try: optconf.waitime = float(jobconf.defaults.waitime)
    except AttributeError: optconf.waitime = 0

if optconf.xdialog:
    dialogs.yesno = tkboxes.ynbox
    messages.failure = tkboxes.msgbox
    messages.success = tkboxes.msgbox

if optconf.sort:
    optconf.filelist.sort(key=natsort)
elif optconf.sortreverse:
    optconf.filelist.sort(key=natsort, reverse=True)

if not jobconf.scheduler:
    messages.cfgerr('<scheduler> No se especificó el nombre del sistema de colas')

if not optconf.scratch:
    if jobconf.defaults.scratch:
        optconf.scratch = jobconf.defaults.scratch
    else:
        messages.cfgerr('<scratch> No se especificó el directorio temporal de escritura por defecto')

optconf.scratch = realpath(optconf.scratch)

if not optconf.queue:
    if jobconf.defaults.queue:
        optconf.queue = jobconf.defaults.queue
    else:
        messages.cfgerr('<default><queue> No se especificó la cola por defecto')

if not jobconf.packagename:
    messages.cfgerr('<title> No se especificó el nombre del programa')

if not jobconf.packagekey:
    messages.cfgerr('<title> No se especificó la clave del programa')

if jobconf.makejobdir:
    try: jobconf.makejobdir = boolStrings[jobconf.makejobdir]
    except KeyError:
        messages.cfgerr('<outputdir> El texto de este tag debe ser "True" or "False"')
else:
    messages.cfgerr('<outputdir> No se especificó si se requiere crear una carpeta de salida')

if 'usempilauncher' in jobconf:
    try: jobconf.usempilauncher = boolStrings[jobconf.usempilauncher]
    except KeyError:
        messages.cfgerr('<usempilauncher> El texto de este tag debe ser "True" o "False"')

if optconf.interactive:
    jobconf.defaults = []

if not jobconf.filenames:
    messages.cfgerr('<filenames> La lista de archivos del programa no existe o está vacía')

if jobconf.inputfiles:
    for item in jobconf.inputfiles:
        for key in item.split('|'):
            if not key in jobconf.filenames:
                messages.cfgerr('<inputfiles><e>{0}</e> El nombre de este archivo de entrada no fue definido'.format(key))
else:
    messages.cfgerr('<inputfiles> La lista de archivos de entrada no existe o está vacía')

if jobconf.outputfiles:
    for item in jobconf.outputfiles:
        for key in item.split('|'):
            if not key in jobconf.filenames:
                messages.cfgerr('<otputfiles><e>{0}</e> El nombre de este archivo de salida no fue definido'.format(key))
else:
    messages.cfgerr('<outputfiles> La lista de archivos de salida no existe o está vacía')

if jobconf.versions:
    if not optconf.version:
        if 'version' in jobconf.defaults:
            if jobconf.defaults.version in jobconf.versions:
                optconf.version = jobconf.defaults.version
            else:
                messages.opterr('La versión establecida por default es inválida')
        else:
            optconf.version = dialogs.chooseone('Seleccione una versión', choices=sorted(list(jobconf.versions), key=str.casefold))
            if not optconf.version in jobconf.versions:
                messages.opterr('La versión seleccionada es inválida')
else:
    messages.cfgerr('<versions> La lista de versiones no existe o está vacía')

if not jobconf.versions[optconf.version].executable:
    messages.cfgerr('No se especificó el ejecutable de la versión', optconf.version)

executable = jobconf.versions[optconf.version].executable
profile = jobconf.versions[optconf.version].profile

optconf.parameters = []
for key in jobconf.parameters:
    parameterdir = realpath(jobconf.parameters[key])
    parameterset = getattr(optconf, key)
    try: options = listdir(parameterdir)
    except FileNotFoundError as e:
        if e.errno == ENOENT:
            messages.cfgerr('El directorio de parámetros', parameterdir, 'no existe')
    if not options:
        messages.cfgerr('El directorio de parámetros', parameterdir, 'está vacío')
    if parameterset is None:
        if key in jobconf.defaults.parameters:
            parameterset = jobconf.defaults.parameters[key]
        else:
            parameterset = dialogs.chooseone('Seleccione un conjunto de parámetros', p(key), choices=sorted(options, key=str.casefold))
    if path.exists(path.join(parameterdir, parameterset)):
        optconf.parameters.append(path.join(parameterdir, parameterset))
    else:
        messages.opterr('La ruta de parámetros', path.join(parameterdir, parameterset), 'no existe')

command = []
environment = []
keywords = {}
control = []

control.append(scheduler.label.format(jobconf.packagename))
control.append(scheduler.queue.format(optconf.queue))
control.append(scheduler.stdout.format(pathjoin(optconf.scratch, (scheduler.jobid, 'out'))))
control.append(scheduler.stderr.format(pathjoin(optconf.scratch, (scheduler.jobid, 'err'))))

if optconf.exechosts:
    control.append(scheduler.hosts.format(optconf.exechosts))

#TODO: MPI support for Slurm
if jobconf.parallelization:
    if jobconf.parallelization.lower() == 'none':
        control.append(scheduler.singlehost)
    elif jobconf.parallelization.lower() == 'openmp':
        control.append(scheduler.ncore.format(optconf.ncore))
        control.append(scheduler.singlehost)
        environment.append('export OMP_NUM_THREADS=' + str(optconf.ncore))
    elif jobconf.parallelization.lower() in mpiLibs:
        if not 'usempilauncher' in jobconf:
            messages.cfgerr('<usempilauncher> No se especificó si el programa es lanzado por mpirun')
        control.append(scheduler.ncore.format(optconf.ncore))
        if optconf.singlehost:
            control.append(scheduler.singlehost)
        if jobconf.usempilauncher:
            command.append(scheduler.mpirun[jobconf.parallelization])
    else:
        messages.cfgerr('El tipo de paralelización ' + jobconf.parallelization + ' no está soportado')
else:
    messages.cfgerr('<parallelization> No se especificó el tipo de paralelización del programa')

environment.extend(scheduler.environment)
environment.extend(jobconf.environment)

for profile in jobconf.profile + profile:
    environment.append(profile)

for var in jobconf.filevars:
    environment.append(var + '=' + jobconf.filenames[jobconf.filevars[var]])

environment.append("shopt -s nullglob extglob")
environment.append("workdir=" + pathjoin(optconf.scratch, scheduler.jobidvar))
environment.append("freeram=$(free -m | tail -n+3 | head -1 | awk '{print $4}')")
environment.append("totalram=$(free -m | tail -n+2 | head -1 | awk '{print $2}')")
environment.append("jobram=$(($ncore*$totalram/$(nproc --all)))")
environment.append("progname=" + jobconf.packagename)

command.append(realpath(executable) if path.sep in executable else executable)

for key in jobconf.optionargs:
    if not jobconf.optionargs[key] in jobconf.filenames:
        messages.cfgerr('<optionargs><e>{0}</e> El nombre de este archivo de entrada/salida no fue definido'.format(key))
    command.append(wordjoin('-' + key, jobconf.filenames[jobconf.optionargs[key]]))

for item in jobconf.positionargs:
    for key in item.split('|'):
        if not key in jobconf.filenames:
            messages.cfgerr('<positionargs><e>{0}</e> El nombre de este archivo de entrada/salida no fue definido'.format(key))
    command.append('@' + p('|'.join(jobconf.filenames[i] for i in item.split('|'))))

if 'stdin' in jobconf:
    try: command.append('0<' + ' ' + jobconf.filenames[jobconf.stdin])
    except KeyError: messages.cfgerr('El nombre de archivo "' + jobconf.stdin + '" en el tag <stdin> no fue definido.')
if 'stdout' in jobconf:
    try: command.append('1>' + ' ' + jobconf.filenames[jobconf.stdout])
    except KeyError: messages.cfgerr('El nombre de archivo "' + jobconf.stdout + '" en el tag <stdout> no fue definido.')
if 'stderr' in jobconf:
    try: command.append('2>' + ' ' + jobconf.filenames[jobconf.stderr])
    except KeyError: messages.cfgerr('El nombre de archivo "' + jobconf.stderr + '" en el tag <stderr> no fue definido.')

if optconf.template:
    if optconf.molfile:
        molpath = Path(optconf.molfile)
        if molpath.is_file():
            keywords['mol0'] = molpath.resolve()
            if molpath.suffix == '.xyz':
                for i, step in enumerate(readxyz(molpath), 1):
                    keywords['mol' + str(i)] = '\n'.join('{0:>2s}  {1:9.4f}  {2:9.4f}  {3:9.4f}'.format(*atom) for atom in step['coords'])
                if not optconf.jobname:
                    optconf.jobname = molpath.stem
            else:
                messages.opterr('Solamente están soportados archivos de coordenadas en formato xyz')
        elif molpath.is_dir():
            messages.opterr('El archivo de coordenadas', molpath, 'es un directorio')
        elif molpath.exists():
            messages.opterr('El archivo de coordenadas', molpath, 'no es un archivo regular')
        else:
            messages.opterr('El archivo de coordenadas', molpath, 'no existe')
    elif not optconf.jobname:
        messages.opterr('Se debe especificar el archivo de coordenadas y/o el nombre del trabajo para poder interpolar')
    
for key in jobconf.formatkeys:
    try: keywords[key] = getattr(optconf, key)
    except AttributeError:
        pass


