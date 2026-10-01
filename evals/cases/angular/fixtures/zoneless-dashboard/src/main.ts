import { bootstrapApplication } from '@angular/platform-browser';
import { provideZonelessChangeDetection } from '@angular/core';
import { Dashboard } from './app/dashboard';

bootstrapApplication(Dashboard, {
  providers: [provideZonelessChangeDetection()],
}).catch((err) => console.error(err));
