(define sum 
  (lambda (xs) 
    (if (= (cdr xs) '())
        (car xs)
        (+ (car xs) (sum (cdr xs))))))
