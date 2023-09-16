program InsertionSort:
    insertionSort(arr) -> array:
        let n = length(arr);
        
        for i in [1..n - 1]:
            let key = arr[i];
            let j = i - 1;
            
            while j >= 0 and arr[j] > key:
                let arr[j + 1] = arr[j];
                let j = j - 1;
            end;
            
            let arr[j + 1] = key;
        end;
        
        return arr;

    main:
        array numbers[15];
        
        for i in [0..14]:
            let numbers[i] = random(1, 100);
        
        output "Original array:", numbers;

        let sortedArray = insertionSort(numbers);
        
        output "Sorted array:", sortedArray;
