import sys
if '--worker-server' in sys.argv:
    from engine import worker_server
    sys.exit(worker_server())
if '--worker' in sys.argv:
    from engine import worker
    sys.exit(worker(sys.argv[sys.argv.index('--worker')+1]))
from refined import Window as MainWindow, main
if __name__ == '__main__':
    main()
