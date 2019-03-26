#!/bin/python
import os
import sys
import psutil
import inspect
import argparse
import subprocess


class Command(object):

    def _install(self,src_dir,build_dir,args=None):
        src_dir=os.path.abspath(src_dir)
        build_dir=os.path.abspath(build_dir)
        if not os.path.isfile(os.path.join(src_dir,"conanfile.txt")):
            raise Exception("conanfile.txt not found at "+src_dir)

        if src_dir == build_dir:
            build_dir=os.path.join(src_dir,"build")

        if not os.path.isdir(build_dir):
            os.path.join(build_dir)

        cmdstring=['conan','install',src_dir,'-if',build_dir]
        if args:
            cmdstring.extend(args)

        print(' '.join(cmdstring))
        subprocess.run(' '.join(cmdstring),shell=True,check=True)
        if not os.path.isfile(os.path.join(build_dir,'conanbuildinfo.cmake')):
            raise Exception("conanbuildinfo.cmake not found at "+build_dir)

    def _configure(self,src_dir,build_dir,args=None,reinstall=False):
        src_dir=os.path.abspath(src_dir)
        build_dir=os.path.abspath(build_dir)
        if src_dir == build_dir:
            build_dir=os.path.join(src_dir,'build')

        if not os.path.isfile(os.path.join(src_dir,"CMakeLists.txt")):
            raise Exception("CMakeLists.txt not found at "+src_dir)

        if reinstall or (not os.path.isfile(os.path.join(build_dir,"conanbuildinfo.cmake"))):
            self._install(src_dir=src_dir,build_dir=build_dir,args=args)

        if os.path.isfile(os.path.join(build_dir,'activate.sh')):
            subprocess.run('. ./activate.sh && cmake '+src_dir,
                shell=True,
                check=True,
                cwd=build_dir)

    def _build(self,src_dir,build_dir,args,reinstall):
        src_dir=os.path.abspath(src_dir)
        build_dir=os.path.abspath(build_dir)
        if src_dir == build_dir:
            build_dir=os.path.join(src_dir,"build")

        if not os.path.isfile(os.path.join(build_dir,'Makefile')):
            print ("Makefile not found @ "+build_dir)
            if not os.path.join(src_dir,'CMakeLists.txt'):
                raise Exception("CMakeLists not found @ "+src_dir)

            else:
                reinstall=True

        if reinstall:
            print(' Reinstall ')
            self._configure(src_dir=src_dir,build_dir=build_dir,args=args,reinstall=reinstall)

        jobs=psutil.cpu_count()
        subprocess.run('cmake --build '+build_dir+' -j '+str(jobs)+' ',shell=True,check=True)

    def _boot(self,src_dir,build_dir,args,reinstall):
        src_dir=os.path.abspath(src_dir)
        build_dir=os.path.abspath(build_dir)
        if src_dir == build_dir:
            build_dir=os.path.join(src_dir,'build')

        if not os.path.isfile(os.path.join(build_dir,'binary.txt')):
            self._configure(src_dir=src_dir,build_dir=build_dir,args=args,reinstall=reinstall)
        filename='service'
        with open(os.path.join(build_dir,'binary.txt')) as binary:
            filename = binary.readline()

        executable=os.path.join(build_dir,filename)
        if not os.path.isfile(executable):
            self._build(src_dir=src_dir,build_dir=build_dir,args=args,reinstall=reinstall)

        if os.path.isfile(executable):
            subprocess.run('. ./activate.sh && boot '+executable,
                shell=True,
                check=True,
                cwd=build_dir)
        else:
            raise Exception("executable not found "+executable)


    def configure(self, *args):
        """Configure includeos service
        """

        parser=argparse.ArgumentParser(description=self.configure.__doc__,prog="includeos configure")
        parser.add_argument("-re",'--reinstall',default=False,
                            help='force re run of conan install and cmake configure')
        parser.add_argument('-bf',"--build-folder",nargs=1,type=str,
                            help='the directory to build the instance in <default build if source == cwd else current directory>')

        parser.add_argument("path",help="path to the source code directory <default = cwd>")

        parser.add_argument('args',nargs=argparse.REMAINDER,help="options passed directly to conan install")
        args=parser.parse_args(*args)
        build_folder='.'
        if args.build_folder:
            build_folder=''.join(args.build_folder)

        print("Build folder "+build_folder)

        self._configure(src_dir=args.path,
            build_dir=build_folder,
            args=args.args,
            reinstall=args.reinstall)
        return

    def build(self, *args):
        """build a includeos service
        """
        parser=argparse.ArgumentParser(description=self.build.__doc__,prog="includeos build")
        parser.add_argument('--reinstall'
            ,help='force re run of conan install and cmake configure'
            ,action="store_true"
        )
        parser.add_argument("-bf",'--build-folder',nargs=1,type=str,help="path to the source code directory <default = cwd>")
        parser.add_argument("path",help="path to the source directory")
        parser.add_argument('args',nargs=argparse.REMAINDER,help="options passed directly to conan install")
        args=parser.parse_args(*args)

        build_dir="."
        if args.build_folder:
            build_dir=''.join(args.build_folder)

        return self._build(src_dir=args.path,
            build_dir=build_dir,
            args=args.args,
            reinstall=args.reinstall)



    def boot(self,*args):
        """boot a includeos service
        """
        parser=argparse.ArgumentParser(description=self.boot.__doc__,prog="includeos build")
        parser.add_argument('--reinstall',action="store_true"
            ,help='force re run of conan install and cmake configure')
        parser.add_argument("-bf",'--build-folder',nargs=1,type=str,help="path to the source code directory <default = cwd>")
        parser.add_argument("path",help="path to the source directory")
        parser.add_argument('args',nargs=argparse.REMAINDER,help="options passed directly to conan install")
        args=parser.parse_args(*args)
        build_folder="."
        if args.build_folder:
            build_folder=''.join(args.build_folder)

        return self._boot(src_dir=args.path,build_dir=build_folder,args=args.args,reinstall=args.reinstall)
        #if args.path:



        #TODO add -pr conan profile..
    def run(self, *args):
        """DONTSHOW: entry point
        """
        #print("RUN")
        try:
            command= args[0][0]
            commands=self._commands()
            function=commands[command]
        except KeyError as exc:
            if command in ["-v","--version"]:
                print("VERSION")
                return False
            self._show_help()
            if command in ["-h", "--help"]:
                return False
            raise Exception("Unknown command %s" % str(exc))
        except IndexError:
            self._show_help()
            return False
        function(args[0][1:])
    def _commands(self):
        """ returns list of available commands
        """
        result = {}
        for method in inspect.getmembers(self,predicate=inspect.ismethod):
            method_name =method[0]
            if not method_name.startswith('_'):
                #method =
                m = method[1]
                if m.__doc__ and not m.__doc__.startswith('DONTSHOW'):
                    result[method_name] = m
        return result

    def help(self,*args):
        commands= self._commands()


def main(args):
    """ main entry point for the includeos application
    """
    #TODO add exit codes
    current_dir=os.getcwd()
    print("args"+str(args))
    cmd=Command()
    err=cmd.run(args)

def run():
    main(sys.argv[1:])


if __name__ == '__main__':
    run()
