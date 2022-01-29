# import os
#
# from pkm_cli.main import main
#
# os.chdir('/home/bennyl/projects/pkm-new/workspace/projects/xxx')
# main(['install'])

def foo(on_x=None, on_y=None, **junk):
    if on_x:
        on_x()

    if on_y:
        on_y()


def main():
    def on_x():
        print("x")

    def on_z():
        print("z")

    foo(**locals())


main()
