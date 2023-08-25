program MaxNumberFinder:
    main:
        int array numbers[100];
        int index = 0;
        let inputLine = input();
        
        while inputLine /= "":
            let numbers[index] = int(inputLine);
            let index = index + 1;
            let inputLine = input();
        end;

        let maxNumber = numbers[0];
        for i in [1..index - 1]:
            if numbers[i] > maxNumber:
                let maxNumber = numbers[i];
            end;
        end;

        output "The maximum number is: ", maxNumber;