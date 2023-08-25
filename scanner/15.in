program BinarySearchAndSort:
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

    binarySearch(arr, target) -> bool:
        let low = 0;
        let high = length(arr) - 1;
        
        while low <= high:
            let mid = (low + high) / 2;
            
            if arr[mid] == target:
                return true;
            elif arr[mid] < target:
                let low = mid + 1;
            else:
                let high = mid - 1;
            end;
        end;
        
        return false;

    main:
        array numbers[15];
        
        for i in [0..14]:
            let numbers[i] = random(1, 100);
        
        output "Original array:", numbers;

        let sortedArray = insertionSort(numbers);
        
        output "Sorted array:", sortedArray;

        let target = random(1, 100);
        let found = binarySearch(sortedArray, target);
        
        if found:
            output "Target", target, "was found in the sorted array.";
        else:
            output "Target", target, "was not found in the sorted array.";