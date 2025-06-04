from concurrent.futures import ProcessPoolExecutor, as_completed
import time

def x(a, b): 
    
    time.sleep(2)
    print('Running x')
    return a ** b

def y(c):
    
    time.sleep(5)
    print('Running y')
    return [i for i in range(c)]

def z(v, a):
    
    time.sleep(1)
    print('Running z')
    return v / a

def a(xout, yout, zout):
    print('running a')
    return [xout ** zout for _ in range(len(yout))]


def main():
    # Input arguments
    x_args = (2, 8)
    y_args = 5
    z_args = (100, 2)

    with ProcessPoolExecutor() as executor:
        # Submit the tasks
        futures = {
            'x': executor.submit(x, *x_args),
            'y': executor.submit(y, y_args),
            'z': executor.submit(z, *z_args),
        }

        # Collect the results
        results = {}
        for key, future in futures.items():
            results[key] = future.result()

    # Now call `a` with the results
    a_result = a(results['x'], results['y'], results['z'])

    print("x result:", results['x'])
    print("y result:", results['y'])
    print("z result:", results['z'])
    print("a result:", a_result)


if __name__ == "__main__":
    main()
