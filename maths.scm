(define fact 
  (lambda (x)
    (if (= x 1)
        1
        (* x (fact (- x 1))))))

(define fibo (lambda (n) 
               (if (or (= n 0) (= n 1))
                   1
                   (+ (fibo (- n 1)) (fibo (- n 2))))))

