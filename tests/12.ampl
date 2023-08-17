program FibonacciCalculator:
    Fibonacci(int n) -> int:
        if n <= 1:
            return n
        else:
            return Fibonacci(n - 1) + Fibonacci(n - 2)
        end

    main:
        int termCount;
        let termCount = 10;
        
        while termCount > 0:
            let fibonacciNumber = Fibonacci(i);
            output("Fibonacci(" .. i .. ") = " .. fibonacciNumber)