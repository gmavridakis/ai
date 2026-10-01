package com.acme.orders;

import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/orders")
public class OrderController {
    private final OrderRepository repository;

    public OrderController(OrderRepository repository) { this.repository = repository; }

    @GetMapping
    public List<Order> list(@RequestParam(defaultValue = "OPEN") String status) {
        return repository.findByStatus(status);
    }
}
