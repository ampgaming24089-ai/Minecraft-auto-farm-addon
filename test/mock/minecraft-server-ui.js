export class ActionFormData {
  title() {
    return this;
  }
  body() {
    return this;
  }
  button() {
    return this;
  }
  show() {
    return Promise.resolve({ canceled: true });
  }
}

export class ModalFormData {
  title() {
    return this;
  }
  slider() {
    return this;
  }
  toggle() {
    return this;
  }
  show() {
    return Promise.resolve({ canceled: true });
  }
}
