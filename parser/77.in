program FibonacciCalculator:
    
    Fibonacci(int n) -> int:
        { recursive fibonacci calculator }
        if n <= 1:
            return n
        else:
            return Fibonacci(n - 1) + Fibonacci(n - 2)
        end

    main:
        { vardefs }
        int termCount;
        int fibonacciNumber;


        let termCount = 10;
        
        while termCount > 0:
            let fibonacciNumber = Fibonacci(termCount);
            output("Fibonacci(" .. termCount .. ") = " .. fibonacciNumber);
            let termCount = termCount - 1;
        end

